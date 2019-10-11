
build:
		docker-compose -f docker-compose.yml up --build -d
		docker-compose -f consumers.yml up --build -d
stop:
		docker-compose -f consumers.yml down
		docker-compose -f docker-compose.yml down

test_setup:
		docker-compose -f docker-compose.yml up --build -d service_bridge

		docker-compose -f docker-compose.yml up --build -d producer consumer
		docker-compose -f docker-compose.yml up --build -d zipkin

test: test_setup
		docker-compose -f docker-compose.yml up --build -d training_api
		docker-compose -f tests.yml up --build test_training

		docker-compose -f docker-compose.yml up --build -d extraction_api
		docker-compose -f tests.yml up --build test_extraction

test_specific: test_setup
		docker-compose -f tests.yml up --build ${Test}


