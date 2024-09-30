zip:
	mkdir -p output
	zip -r output/source.zip runners utils resources index.js mongo.js package.json docker-compose.yaml Dockerfile

upload:
	scp ./output/source.zip noname@10.7.0.50:~/eigenphy_crawler/source.zip
