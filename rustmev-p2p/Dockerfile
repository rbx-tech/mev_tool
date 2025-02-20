FROM rust:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app/mevp2p

COPY . .

RUN cargo build --release

ENV PATH="/app/mevp2p/target/release:${PATH}"

CMD ["./target/release/rust-mevp2p"]
