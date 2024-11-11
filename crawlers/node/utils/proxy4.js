import fs from 'node:fs/promises';
import axios from 'axios';
import { SocksProxyAgent } from 'socks-proxy-agent';
import axiosRetry from 'axios-retry';

export class Proxy4 {
  constructor(host) {
    this.host = host;
  }

  static hosts = [];
  static lastIndex = -1;
  static async genNew() {
    const host = await Proxy4.genRandomHost();
    return new Proxy4(host);
  }

  static async genRandomHost() {
    if (!Proxy4.hosts.length) {
      const content = await fs.readFile('../resources/proxy_socks5.txt', { encoding: 'utf8' });
      Proxy4.hosts = content.split('\n');
    }
    if (Proxy4.lastIndex >= Proxy4.hosts.length) {
      Proxy4.lastIndex = -1;
    }
    return Proxy4.hosts[++Proxy4.lastIndex];
  }

  toClient() {
    let proxyUrl = `socks5://${this.host}`;
    const agent = new SocksProxyAgent(proxyUrl);
    const axiosIns = axios.create({
      httpsAgent: agent,
      httpAgent: agent,
    });
    axiosRetry(axiosIns, { retries: 3, retryDelay: axiosRetry.exponentialDelay });
    return axiosIns;
  }
}
