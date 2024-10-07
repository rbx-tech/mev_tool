zip:
	mkdir -p output
	rm -rf output/source.zip
	zip -r output/source.zip runners utils resources index.js mongo.js package.json docker-compose.yaml Dockerfile

upload:
	scp ./output/source.zip noname@10.7.0.50:/mnt/nvme2/mev_crawlers/source.zip

# build_image:
# 	docker build -t 
# 	docker save -o resources/nodejs mev_crawlers
