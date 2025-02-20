use enr::secp256k1::{rand, SecretKey};
use enr::secp256k1::{rand::thread_rng, SECP256K1};
use futures::SinkExt;
use reth_discv4::{DiscoveryUpdate, Discv4, Discv4Config, NodeRecord};
use reth_ecies::stream::ECIESStream;
use reth_eth_wire::errors::{P2PHandshakeError, P2PStreamError};
use reth_eth_wire::{
    CanDisconnect, EthMessage, EthStream, EthVersion, HelloMessage, P2PStream, ProtocolMessage, Status, UnauthedP2PStream,
};
use reth_network_peers::pk2id;
use std::{net::SocketAddr, str::FromStr};
use tokio::net::TcpStream;
use tokio_stream::wrappers::ReceiverStream;
use tokio_stream::StreamExt;

type AuthedP2PStream = P2PStream<ECIESStream<TcpStream>>;
type AuthedEthStream = EthStream<P2PStream<ECIESStream<TcpStream>>>;

pub struct DevP2P {}

pub enum DevP2PHandsharkError {}

impl DevP2P {
    pub async fn discv4(bootnodes: Vec<NodeRecord>) -> ReceiverStream<DiscoveryUpdate> {
        // let fork_id = ForkId {
        //     hash: ForkHash(hex!("743f3d89")),
        //     next: 16191202,
        // };
        let config = Discv4Config::builder()
            .add_boot_nodes(bootnodes)
            // .add_eip868_pair("eth", fork_id)
            .max_find_node_failures(10)
            .enable_lookup(true)
            .build();

        let socket = SocketAddr::from_str("0.0.0.0:0").unwrap();
        let (secret_key, pk) = SECP256K1.generate_keypair(&mut thread_rng());

        let local_nr = NodeRecord::new(socket, pk2id(&pk));
        let (_discv4, mut service) = Discv4::bind(socket, local_nr, secret_key, config).await.unwrap();
        let updates = service.update_stream();
        let _handle = service.spawn();
        return updates;
    }

    pub async fn ping_node(nr: NodeRecord) -> eyre::Result<(HelloMessage, Status)> {
        let (p2p_stream, their_hello) = Self::handshake_p2p(nr).await?;
        let (mut p2p_stream, status) = Self::handshake_eth(p2p_stream).await?;
        let _ = p2p_stream.disconnect(reth_eth_wire::DisconnectReason::ClientQuitting).await;
        return Ok((their_hello, status));
    }

    pub async fn handshake_p2p(peer: NodeRecord) -> eyre::Result<(AuthedP2PStream, HelloMessage)> {
        let our_key = SecretKey::new(&mut rand::thread_rng());
        let outgoing = TcpStream::connect((peer.address, peer.tcp_port)).await?;
        let ecies_stream = ECIESStream::connect(outgoing, our_key, peer.id).await?;

        let our_peer_id = pk2id(&our_key.public_key(SECP256K1));
        let our_hello = HelloMessage::builder(our_peer_id).build();
        let result = UnauthedP2PStream::new(ecies_stream).handshake(our_hello).await?;
        Ok(result)
    }

    pub async fn handshake_eth(mut p2p_stream: AuthedP2PStream) -> eyre::Result<(AuthedEthStream, Status)> {
        let status = Status::builder().build();
        p2p_stream
            .send(alloy_rlp::encode(ProtocolMessage::from(EthMessage::Status(status))).into())
            .await?;

        let their_msg_res = p2p_stream.next().await;

        if their_msg_res.is_none() {
            return Err(eyre::ErrReport::new(P2PHandshakeError::NoResponse));
        }

        let their_msg = match their_msg_res.unwrap() {
            Ok(msg) => msg,
            Err(_) => {
                return Err(eyre::ErrReport::new(P2PHandshakeError::NoResponse));
            }
        };

        let p2p_version = p2p_stream.shared_capabilities().eth()?.version();
        let version = EthVersion::try_from(p2p_version)?;

        let msg = ProtocolMessage::decode_message(version, &mut their_msg.as_ref())?;
        match msg.message {
            EthMessage::Status(status) => {
                let eth_stream = EthStream::new(version, p2p_stream);
                return Ok((eth_stream, status));
            }
            _ => Err(eyre::ErrReport::new(P2PStreamError::EmptyProtocolMessage)),
        }
    }
}
