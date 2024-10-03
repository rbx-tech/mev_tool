import axios from 'axios'
import { SocksProxyAgent } from 'socks-proxy-agent';
import axiosRetry from 'axios-retry';

const ipPrefix = "2604:4300:f38::"
const passwd = "xFkzihNm"
const schema = "socks5h"
const host = "173.208.140.106:22225"
const userPrefix = "inf-ip-"
const prefixSize = 50
const subPrefixSize = 64


export class Proxy6 {
  constructor(user) {
      this.user = user;
  }

  static genNew() {
      const newAddr = Proxy6.genRandomIp(ipPrefix, prefixSize, subPrefixSize);
      const user = encodeURIComponent(`${userPrefix}${newAddr}`);
      return new Proxy6(user);
  }

  static genRandomIp(prefix) {
    // Split the prefix by ':' and pad it to 8 groups (standard IPv6 address has 8 groups of 16-bit each)
    const prefixParts = prefix.split(':');
    const filledParts = [...prefixParts, ...Array(8 - prefixParts.length).fill('0000')];
    
    // The first three groups are fixed (based on /48 prefix)
    const fixedPart = filledParts.slice(0, 3).join(':');
    
    // Generate random values for the remaining 5 groups (each group is 16 bits)
    let randomPart = [];
    for (let i = 0; i < 5; i++) {
        // Generate a random 16-bit hexadecimal value
        randomPart.push(Math.floor(Math.random() * 0x10000).toString(16).padStart(4, '0'));
    }
    
    // Combine the fixed part and the random part
    return fixedPart + ':' + randomPart.join(':');
  }

  toClient() {
      let proxyUrl = `${schema}://${this.user}:${passwd}@${host}`;
      const agent = new SocksProxyAgent(proxyUrl);
      const axiosIns = axios.create({
          httpsAgent: agent,
      });
      axiosIns.defaults.timeout = 2 * 60_000;
      axiosRetry(axiosIns, { retries: 3, retryDelay: axiosRetry.exponentialDelay });
      return axiosIns;
  }
}
