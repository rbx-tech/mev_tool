zip:
	mkdir -p output
	zip -r output/source.zip runners utils index.js mongo.js package.json docker-compose.yaml Dockerfile proxy_socks5.txt

upload:
	scp ./output/source.zip noname@10.7.0.50:~/eigenphy_crawler/source.zip
