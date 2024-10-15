zip:
	mkdir -p output
	rm -rf output/source.zip
	zip -r output/source.zip node/ python/ resources/ docker-compose.yaml -x "./node/node_modules/*" "node/package-lock.json" "./python/venv/*" \*__pycache__\* @

upload:
	scp ./output/source.zip noname@10.7.0.50:/mnt/nvme2/mev_crawlers/source.zip

# build_image:
# 	docker build -t 
# 	docker save -o resources/nodejs mev_crawlers
