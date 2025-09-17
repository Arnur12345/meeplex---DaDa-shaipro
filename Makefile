.PHONY: all setup submodules env force-env download-model build-bot-image build up down ps logs test migrate makemigrations init-db stamp-db migrate-or-init llm-health llm-logs llm-test llm-streams llm-restart wake-word-test wake-word-config

# Default target: Sets up everything and starts the services
all: setup-env build-bot-image build up migrate-or-init test

# Target to set up only the environment without Docker
# Ensure .env is created based on TARGET *before* other setup steps
setup-env: env submodules download-model
	@echo "Environment setup complete."
	@echo "The 'env' target (now called by setup-env) handles .env creation/preservation:"
	@echo "  - If .env exists, it is preserved."
	@echo "  - If .env does not exist, it is created based on the TARGET variable (e.g., 'make setup-env TARGET=gpu')."
	@echo "  - If .env is created and no TARGET is specified, it defaults to 'cpu'."
	@echo "To force an overwrite of an existing .env file, use 'make force-env TARGET=cpu/gpu'."

# Target to perform all initial setup steps
setup: setup-env build-bot-image
	@echo "Setup complete."

# Initialize and update Git submodules
submodules:
	@echo "---> Initializing and updating Git submodules..."
	@git submodule update --init --recursive

# Default bot image tag if not specified in .env
BOT_IMAGE_NAME ?= vexa-bot:dev

# Check if Docker daemon is running
check_docker:
	@echo "---> Checking if Docker is running..."
	@if ! docker info > /dev/null 2>&1; then \
		echo "ERROR: Docker is not running. Please start Docker Desktop or Docker daemon first."; \
		exit 1; \
	fi
	@echo "---> Docker is running."

# Include .env file if it exists for environment variables 
-include .env

# Create .env file from example
env:
ifndef TARGET
	$(info TARGET not set. Defaulting to cpu. Use 'make env TARGET=cpu' or 'make env TARGET=gpu')
	$(eval TARGET := cpu)
endif
	@echo "---> Checking .env file for TARGET=$(TARGET)..."
	@if [ -f .env ]; then \
		echo "*** .env file already exists. Keeping existing file. ***"; \
		echo "*** To force recreation, delete .env first or use 'make force-env TARGET=$(TARGET)'. ***"; \
	elif [ "$(TARGET)" = "cpu" ]; then \
		if [ ! -f env-example.cpu ]; then \
			echo "env-example.cpu not found. Creating default one."; \
			echo "ADMIN_API_TOKEN=token" > env-example.cpu; \
			echo "LANGUAGE_DETECTION_SEGMENTS=10" >> env-example.cpu; \
			echo "VAD_FILTER_THRESHOLD=0.5" >> env-example.cpu; \
			echo "WHISPER_MODEL_SIZE=tiny" >> env-example.cpu; \
			echo "DEVICE_TYPE=cpu" >> env-example.cpu; \
			echo "BOT_IMAGE_NAME=vexa-bot:dev" >> env-example.cpu; \
			echo "# Exposed Host Ports" >> env-example.cpu; \
			echo "API_GATEWAY_HOST_PORT=8056" >> env-example.cpu; \
			echo "ADMIN_API_HOST_PORT=8057" >> env-example.cpu; \
			echo "TRAEFIK_WEB_HOST_PORT=9090" >> env-example.cpu; \
			echo "TRAEFIK_DASHBOARD_HOST_PORT=8085" >> env-example.cpu; \
			echo "TRANSCRIPTION_COLLECTOR_HOST_PORT=8123" >> env-example.cpu; \
			echo "LLM_PROCESSOR_HOST_PORT=8124" >> env-example.cpu; \
			echo "TTS_PROCESSOR_HOST_PORT=8125" >> env-example.cpu; \
			echo "POSTGRES_HOST_PORT=5438" >> env-example.cpu; \
		fi; \
		cp env-example.cpu .env; \
		echo "*** .env file created from env-example.cpu. Please review it. ***"; \
	elif [ "$(TARGET)" = "gpu" ]; then \
		if [ ! -f env-example.gpu ]; then \
			echo "env-example.gpu not found. Creating default one."; \
			echo "ADMIN_API_TOKEN=token" > env-example.gpu; \
			echo "LANGUAGE_DETECTION_SEGMENTS=10" >> env-example.gpu; \
			echo "VAD_FILTER_THRESHOLD=0.5" >> env-example.gpu; \
			echo "WHISPER_MODEL_SIZE=medium" >> env-example.gpu; \
			echo "DEVICE_TYPE=cuda" >> env-example.gpu; \
			echo "BOT_IMAGE_NAME=vexa-bot:dev" >> env-example.gpu; \
			echo "# Exposed Host Ports" >> env-example.gpu; \
			echo "API_GATEWAY_HOST_PORT=8056" >> env-example.gpu; \
			echo "ADMIN_API_HOST_PORT=8057" >> env-example.gpu; \
			echo "TRAEFIK_WEB_HOST_PORT=9090" >> env-example.gpu; \
			echo "TRAEFIK_DASHBOARD_HOST_PORT=8085" >> env-example.gpu; \
			echo "TRANSCRIPTION_COLLECTOR_HOST_PORT=8123" >> env-example.gpu; \
			echo "LLM_PROCESSOR_HOST_PORT=8124" >> env-example.gpu; \
			echo "TTS_PROCESSOR_HOST_PORT=8125" >> env-example.gpu; \
			echo "POSTGRES_HOST_PORT=5438" >> env-example.gpu; \
		fi; \
		cp env-example.gpu .env; \
		echo "*** .env file created from env-example.gpu. Please review it. ***"; \
	else \
		echo "Error: TARGET must be 'cpu' or 'gpu'. Usage: make env TARGET=<cpu|gpu>"; \
		exit 1; \
	fi

# Force create .env file from example (overwrite existing)
force-env:
ifndef TARGET
	$(info TARGET not set. Defaulting to cpu. Use 'make force-env TARGET=cpu' or 'make force-env TARGET=gpu')
	$(eval TARGET := cpu)
endif
	@echo "---> Creating .env file for TARGET=$(TARGET) (forcing overwrite)..."
	@if [ "$(TARGET)" = "cpu" ]; then \
		if [ ! -f env-example.cpu ]; then \
			echo "env-example.cpu not found. Creating default one."; \
			echo "ADMIN_API_TOKEN=token" > env-example.cpu; \
			echo "LANGUAGE_DETECTION_SEGMENTS=10" >> env-example.cpu; \
			echo "VAD_FILTER_THRESHOLD=0.5" >> env-example.cpu; \
			echo "WHISPER_MODEL_SIZE=tiny" >> env-example.cpu; \
			echo "DEVICE_TYPE=cpu" >> env-example.cpu; \
			echo "BOT_IMAGE_NAME=vexa-bot:dev" >> env-example.cpu; \
			echo "# Exposed Host Ports" >> env-example.cpu; \
			echo "API_GATEWAY_HOST_PORT=8056" >> env-example.cpu; \
			echo "ADMIN_API_HOST_PORT=8057" >> env-example.cpu; \
			echo "TRAEFIK_WEB_HOST_PORT=9090" >> env-example.cpu; \
			echo "TRAEFIK_DASHBOARD_HOST_PORT=8085" >> env-example.cpu; \
			echo "TRANSCRIPTION_COLLECTOR_HOST_PORT=8123" >> env-example.cpu; \
			echo "LLM_PROCESSOR_HOST_PORT=8124" >> env-example.cpu; \
			echo "TTS_PROCESSOR_HOST_PORT=8125" >> env-example.cpu; \
			echo "POSTGRES_HOST_PORT=5438" >> env-example.cpu; \
		fi; \
		cp env-example.cpu .env; \
		echo "*** .env file created from env-example.cpu. Please review it. ***"; \
	elif [ "$(TARGET)" = "gpu" ]; then \
		if [ ! -f env-example.gpu ]; then \
			echo "env-example.gpu not found. Creating default one."; \
			echo "ADMIN_API_TOKEN=token" > env-example.gpu; \
			echo "LANGUAGE_DETECTION_SEGMENTS=10" >> env-example.gpu; \
			echo "VAD_FILTER_THRESHOLD=0.5" >> env-example.gpu; \
			echo "WHISPER_MODEL_SIZE=medium" >> env-example.gpu; \
			echo "DEVICE_TYPE=cuda" >> env-example.gpu; \
			echo "BOT_IMAGE_NAME=vexa-bot:dev" >> env-example.gpu; \
			echo "# Exposed Host Ports" >> env-example.gpu; \
			echo "API_GATEWAY_HOST_PORT=8056" >> env-example.gpu; \
			echo "ADMIN_API_HOST_PORT=8057" >> env-example.gpu; \
			echo "TRAEFIK_WEB_HOST_PORT=9090" >> env-example.gpu; \
			echo "TRAEFIK_DASHBOARD_HOST_PORT=8085" >> env-example.gpu; \
			echo "TRANSCRIPTION_COLLECTOR_HOST_PORT=8123" >> env-example.gpu; \
			echo "LLM_PROCESSOR_HOST_PORT=8124" >> env-example.gpu; \
			echo "TTS_PROCESSOR_HOST_PORT=8125" >> env-example.gpu; \
			echo "POSTGRES_HOST_PORT=5438" >> env-example.gpu; \
		fi; \
		cp env-example.gpu .env; \
		echo "*** .env file created from env-example.gpu. Please review it. ***"; \
	else \
		echo "Error: TARGET must be 'cpu' or 'gpu'. Usage: make force-env TARGET=<cpu|gpu>"; \
		exit 1; \
	fi

# Download the Whisper model
download-model:
	@echo "---> Creating ./hub directory if it doesn't exist..."
	@mkdir -p ./hub
	@echo "---> Ensuring ./hub directory is writable..."
	@chmod u+w ./hub
	@echo "---> Preparing Python virtual environment for model download..."
	@if [ ! -d .venv ]; then \
		python3 -m venv .venv; \
	fi
	@echo "---> Upgrading pip in venv..."
	@. .venv/bin/activate && python -m pip install --upgrade pip >/dev/null 2>&1 || true
	@echo "---> Installing Python requirements into venv (this may take a while)..."
	@. .venv/bin/activate && python -m pip install --no-cache-dir -r requirements.txt >/dev/null 2>&1 || true
	@echo "---> Downloading Whisper model (this may take a while)..."
	@. .venv/bin/activate && python download_model.py

# Build the standalone vexa-bot image
# Uses BOT_IMAGE_NAME from .env if available, otherwise falls back to default
build-bot-image: check_docker
	@if [ -f .env ]; then \
		ENV_BOT_IMAGE_NAME=$$(grep BOT_IMAGE_NAME .env | cut -d= -f2); \
		if [ -n "$$ENV_BOT_IMAGE_NAME" ]; then \
			echo "---> Building $$ENV_BOT_IMAGE_NAME image (from .env)..."; \
			docker build -t $$ENV_BOT_IMAGE_NAME -f services/vexa-bot/core/Dockerfile ./services/vexa-bot/core; \
		else \
			echo "---> Building $(BOT_IMAGE_NAME) image (BOT_IMAGE_NAME not found in .env)..."; \
			docker build -t $(BOT_IMAGE_NAME) -f services/vexa-bot/core/Dockerfile ./services/vexa-bot/core; \
		fi; \
	else \
		echo "---> Building $(BOT_IMAGE_NAME) image (.env file not found)..."; \
		docker build -t $(BOT_IMAGE_NAME) -f services/vexa-bot/core/Dockerfile ./services/vexa-bot/core; \
	fi

# Build Docker Compose service images
build: check_docker
	@echo "---> Building Docker images..."
	@if [ "$(TARGET)" = "cpu" ]; then \
		echo "---> Building with 'cpu' profile (includes whisperlive-cpu)..."; \
		docker compose --profile cpu build; \
	elif [ "$(TARGET)" = "gpu" ]; then \
		echo "---> Building with 'gpu' profile (includes whisperlive GPU)..."; \
		docker compose --profile gpu build; \
	else \
		echo "---> TARGET not explicitly set, defaulting to CPU mode. 'whisperlive' (GPU) will not be built."; \
		docker compose --profile cpu build; \
	fi

# Start services in detached mode
up: check_docker
	@echo "---> Starting Docker Compose services..."
	@if [ "$(TARGET)" = "cpu" ]; then \
		echo "---> Activating 'cpu' profile to start whisperlive-cpu along with other services..."; \
		docker compose --profile cpu up -d; \
	elif [ "$(TARGET)" = "gpu" ]; then \
		echo "---> Starting services for GPU. This will start 'whisperlive' (for GPU) and other default services. 'whisperlive-cpu' (profile=cpu) will not be started."; \
		docker compose --profile gpu up -d; \
	else \
		echo "---> TARGET not explicitly set, defaulting to CPU mode. 'whisperlive' (GPU) will not be started."; \
		docker compose --profile cpu up -d; \
	fi

# Stop services
down: check_docker
	@echo "---> Stopping Docker Compose services..."
	@docker compose down

# Show container status
ps: check_docker
	@docker compose ps

# Tail logs for all services
logs:
	@docker compose logs -f

# Run the interaction test script
test: check_docker
	@echo "---> Running test script..."
	@echo "---> API Documentation URLs:"
	@if [ -f .env ]; then \
		API_PORT=$$(grep -E '^[[:space:]]*API_GATEWAY_HOST_PORT=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//'); \
		ADMIN_PORT=$$(grep -E '^[[:space:]]*ADMIN_API_HOST_PORT=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//'); \
		LLM_PORT=$$(grep -E '^[[:space:]]*LLM_PROCESSOR_HOST_PORT=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//'); \
		TTS_PORT=$$(grep -E '^[[:space:]]*TTS_PROCESSOR_HOST_PORT=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//'); \
		[ -z "$$API_PORT" ] && API_PORT=8056; \
		[ -z "$$ADMIN_PORT" ] && ADMIN_PORT=8057; \
		[ -z "$$LLM_PORT" ] && LLM_PORT=8124; \
		[ -z "$$TTS_PORT" ] && TTS_PORT=8125; \
		echo "    Main API:  http://localhost:$$API_PORT/docs"; \
		echo "    Admin API: http://localhost:$$ADMIN_PORT/docs"; \
		echo "    LLM API:   http://localhost:$$LLM_PORT/docs"; \
		echo "    TTS API:   http://localhost:$$TTS_PORT/docs"; \
	else \
		echo "    Main API:  http://localhost:8056/docs"; \
		echo "    Admin API: http://localhost:8057/docs"; \
		echo "    LLM API:   http://localhost:8124/docs"; \
		echo "    TTS API:   http://localhost:8125/docs"; \
	fi
	@echo ""
	@echo "---> Enhanced Wake Word Detection Available:"
	@echo "    Test wake word patterns: make wake-word-test"
	@echo "    View configuration:      make wake-word-config"
	@echo "    Monitor wake word logs:  make logs | grep 'WakeWord Detected'"
	@echo ""
	@echo "---> TTS Audio Processing Available:"
	@echo "    Test TTS generation:     make tts-test"
	@echo "    Monitor TTS streams:     make tts-streams"
	@echo "    View TTS statistics:     make tts-stats"
	@echo "    Test full pipeline:      make tts-pipeline-test"
	@echo ""
	@chmod +x run_vexa_interaction.sh
	@./run_vexa_interaction.sh

# --- Database Migration Commands ---

# Smart migration: detects if database is fresh, legacy, or already Alembic-managed.
# This is the primary target for ensuring the database schema is up to date.
migrate-or-init: check_docker
	@echo "---> Starting smart database migration/initialization..."; \
	set -e; \
	if ! docker compose ps -q postgres | grep -q .; then \
		echo "ERROR: PostgreSQL container is not running. Please run 'make up' first."; \
		exit 1; \
	fi; \
	echo "---> Waiting for database to be ready..."; \
	count=0; \
	while ! docker compose exec -T postgres pg_isready -U postgres -d vexa -q; do \
		if [ $$count -ge 12 ]; then \
			echo "ERROR: Database did not become ready in 60 seconds."; \
			exit 1; \
		fi; \
		echo "Database not ready, waiting 5 seconds..."; \
		sleep 5; \
		count=$$((count+1)); \
	done; \
	echo "---> Database is ready. Checking its state..."; \
	if docker compose exec -T postgres psql -U postgres -d vexa -t -c "SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version';" | grep -q 1; then \
		echo "STATE: Alembic-managed database detected."; \
		echo "ACTION: Running standard migrations to catch up to 'head'..."; \
		$(MAKE) migrate; \
	elif docker compose exec -T postgres psql -U postgres -d vexa -t -c "SELECT 1 FROM information_schema.tables WHERE table_name = 'meetings';" | grep -q 1; then \
		echo "STATE: Legacy (non-Alembic) database detected."; \
		echo "ACTION: Stamping at 'base' and migrating to 'head' to bring it under Alembic control..."; \
		docker compose exec -T transcription-collector alembic -c /app/alembic.ini stamp base; \
		$(MAKE) migrate; \
	else \
		echo "STATE: Fresh, empty database detected."; \
		echo "ACTION: Creating schema directly from models and stamping at revision dc59a1c03d1f..."; \
		docker compose exec -T transcription-collector python -c "import asyncio; from shared_models.database import init_db; asyncio.run(init_db())"; \
		docker compose exec -T transcription-collector alembic -c /app/alembic.ini stamp dc59a1c03d1f; \
	fi; \
	echo "---> Smart database migration/initialization complete!"

# Apply all pending migrations to bring database to latest version
migrate: check_docker
	@echo "---> Applying database migrations..."
	@if ! docker compose ps postgres | grep -q "Up"; then \
		echo "ERROR: PostgreSQL container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@# Preflight: if currently at dc59a1c03d1f and users.data already exists, stamp next revision
	@current_version=$$(docker compose exec -T transcription-collector alembic -c /app/alembic.ini current 2>/dev/null | grep -E '^[a-f0-9]{12}' | head -1 || echo ""); \
	if [ "$$current_version" = "dc59a1c03d1f" ]; then \
		if docker compose exec -T postgres psql -U postgres -d vexa -t -c "SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'data';" | grep -q 1; then \
			echo "---> Preflight: detected existing column users.data. Stamping 5befe308fa8b..."; \
			docker compose exec -T transcription-collector alembic -c /app/alembic.ini stamp 5befe308fa8b; \
		fi; \
	fi
	@echo "---> Running alembic upgrade head..."
	@docker compose exec -T transcription-collector alembic -c /app/alembic.ini upgrade head

# Create a new migration file based on model changes
makemigrations: check_docker
	@if [ -z "$(M)" ]; then \
		echo "Usage: make makemigrations M=\"your migration message\""; \
		echo "Example: make makemigrations M=\"Add user profile table\""; \
		exit 1; \
	fi
	@echo "---> Creating new migration: $(M)"
	@if ! docker compose ps postgres | grep -q "Up"; then \
		echo "ERROR: PostgreSQL container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@docker compose exec -T transcription-collector alembic -c /app/alembic.ini revision --autogenerate -m "$(M)"

# Initialize the database (first time setup) - creates tables and stamps with latest revision
init-db: check_docker
	@echo "---> Initializing database and stamping with Alembic..."
	docker compose run --rm transcription-collector python -c "import asyncio; from shared_models.database import init_db; asyncio.run(init_db())"
	docker compose run --rm transcription-collector alembic -c /app/alembic.ini stamp head
	@echo "---> Database initialized and stamped."

# Stamp existing database with current version (for existing installations)
stamp-db: check_docker
	@echo "---> Stamping existing database with current migration version..."
	@if ! docker compose ps postgres | grep -q "Up"; then \
		echo "ERROR: PostgreSQL container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@docker compose exec -T transcription-collector alembic -c /app/alembic.ini stamp head
	@echo "---> Database stamped successfully!"

# Show current migration status
migration-status: check_docker
	@echo "---> Checking migration status..."
	@if ! docker compose ps postgres | grep -q "Up"; then \
		echo "ERROR: PostgreSQL container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@echo "---> Current database version:"
	@docker compose exec -T transcription-collector alembic -c /app/alembic.ini current
	@echo "---> Migration history:"
	@docker compose exec -T transcription-collector alembic -c /app/alembic.ini history --verbose

# --- End Database Migration Commands ---

# --- LLM-Processor Service Commands ---

# Check LLM-processor service health
llm-health: check_docker
	@echo "---> Checking LLM-processor service health..."
	@if ! docker compose ps llm-processor | grep -q "Up"; then \
		echo "ERROR: LLM-processor container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@if [ -f .env ]; then \
		LLM_PORT=$$(grep -E '^[[:space:]]*LLM_PROCESSOR_HOST_PORT=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//'); \
		[ -z "$$LLM_PORT" ] && LLM_PORT=8124; \
		echo "---> LLM-processor health check:"; \
		curl -f http://localhost:$$LLM_PORT/health 2>/dev/null || echo "Health check failed"; \
	else \
		echo "---> LLM-processor health check:"; \
		curl -f http://localhost:8124/health 2>/dev/null || echo "Health check failed"; \
	fi

# Show LLM-processor service logs
llm-logs:
	@echo "---> Showing LLM-processor service logs..."
	@docker compose logs -f llm-processor

# Test LLM-processor generation endpoint
llm-test: check_docker
	@echo "---> Testing LLM-processor generation endpoint..."
	@if ! docker compose ps llm-processor | grep -q "Up"; then \
		echo "ERROR: LLM-processor container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@if [ -f .env ]; then \
		LLM_PORT=$$(grep -E '^[[:space:]]*LLM_PROCESSOR_HOST_PORT=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//'); \
		[ -z "$$LLM_PORT" ] && LLM_PORT=8124; \
		echo "---> Testing generation endpoint at http://localhost:$$LLM_PORT/generate"; \
		curl -X POST http://localhost:$$LLM_PORT/generate \
			-H "Content-Type: application/json" \
			-d '{"question": "Hello Raven, how are you?", "context": "Test from Makefile"}' 2>/dev/null || echo "Generation test failed"; \
	else \
		echo "---> Testing generation endpoint at http://localhost:8124/generate"; \
		curl -X POST http://localhost:8124/generate \
			-H "Content-Type: application/json" \
			-d '{"question": "Hello Raven, how are you?", "context": "Test from Makefile"}' 2>/dev/null || echo "Generation test failed"; \
	fi

# Monitor Redis streams related to LLM-processor
llm-streams: check_docker
	@echo "---> Monitoring LLM-processor Redis streams..."
	@if ! docker compose ps redis | grep -q "Up"; then \
		echo "ERROR: Redis container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@echo "---> Checking hey_raven_commands stream:"
	@docker compose exec -T redis redis-cli XINFO STREAM hey_raven_commands 2>/dev/null || echo "Stream hey_raven_commands not found"
	@echo "---> Checking llm_responses stream:"
	@docker compose exec -T redis redis-cli XINFO STREAM llm_responses 2>/dev/null || echo "Stream llm_responses not found"
	@echo "---> Checking consumer groups:"
	@docker compose exec -T redis redis-cli XINFO GROUPS hey_raven_commands 2>/dev/null || echo "No consumer groups for hey_raven_commands"
	@docker compose exec -T redis redis-cli XINFO GROUPS llm_responses 2>/dev/null || echo "No consumer groups for llm_responses"

# Restart only the LLM-processor service
llm-restart: check_docker
	@echo "---> Restarting LLM-processor service..."
	@docker compose restart llm-processor
	@echo "---> LLM-processor service restarted."

# Test Enhanced Wake Word Detection
wake-word-test: check_docker
	@echo "---> Testing Enhanced Wake Word Detection..."
	@if ! docker compose ps transcription-collector | grep -q "Up"; then \
		echo "ERROR: Transcription-collector container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@echo "Testing various wake word patterns:"
	@echo "1. Testing 'hey raven what time is it?'"
	@echo "2. Testing 'hello raven can you help me?'"
	@echo "3. Testing 'hi raven where am I?'"
	@echo "4. Testing 'okay raven tell me about the weather'"
	@echo "5. Testing 'excuse me raven how do I...?'"
	@echo "6. Testing 'raven what is the status?'"
	@echo "7. Testing fuzzy matching: 'hey haven what time is it?'"
	@echo ""
	@echo "Check logs with: make logs | grep 'WakeWord Detected'"
	@echo "Monitor Redis streams with: make llm-streams"

# Display Wake Word Configuration
wake-word-config:
	@echo "---> Wake Word Detection Configuration:"
	@echo ""
	@echo "Configuration File: config/wake_word_config.json"
	@echo ""
	@echo "Environment Variables (from .env):"
	@if [ -f .env ]; then \
		echo "  WAKE_WORD_CONFIG_PATH: $$(grep -E '^[[:space:]]*WAKE_WORD_CONFIG_PATH=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//' || echo 'Not set (default: /app/config/wake_word_config.json)')"; \
		echo "  WAKE_WORD_SENSITIVITY: $$(grep -E '^[[:space:]]*WAKE_WORD_SENSITIVITY=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//' || echo 'Not set (default: 0.8)')"; \
		echo "  WAKE_WORD_DEBUG_MODE: $$(grep -E '^[[:space:]]*WAKE_WORD_DEBUG_MODE=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//' || echo 'Not set (default: false)')"; \
		echo "  WAKE_WORD_RATE_LIMIT_ENABLED: $$(grep -E '^[[:space:]]*WAKE_WORD_RATE_LIMIT_ENABLED=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//' || echo 'Not set (default: true)')"; \
		echo "  WAKE_WORD_FUZZY_MATCHING: $$(grep -E '^[[:space:]]*WAKE_WORD_FUZZY_MATCHING=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//' || echo 'Not set (default: true)')"; \
		echo "  WAKE_WORD_COOLDOWN_SECONDS: $$(grep -E '^[[:space:]]*WAKE_WORD_COOLDOWN_SECONDS=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//' || echo 'Not set (default: 3)')"; \
		echo "  WAKE_WORD_MAX_PER_MINUTE: $$(grep -E '^[[:space:]]*WAKE_WORD_MAX_PER_MINUTE=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//' || echo 'Not set (default: 15)')"; \
	else \
		echo "  .env file not found. Using default values."; \
	fi
	@echo ""
	@echo "Wake Word Patterns Available:"
	@echo "  Primary: hey raven, hello raven, hi raven"
	@echo "  Secondary: okay raven, excuse me raven, raven"
	@echo "  Conversational: raven can you, raven help me, raven tell me"
	@echo "  Question: raven what, raven where, raven when, raven who, raven why, raven how"
	@echo "  Punctuation: raven?, raven,"
	@echo "  Fuzzy Matching: hey haven → hey raven (handles ASR errors)"
	@echo ""
	@echo "Rate Limiting:"
	@echo "  Cooldown: 3 seconds between detections per session"
	@echo "  Max Rate: 15 detections per minute per session"
	@echo ""
	@echo "Use 'make wake-word-test' to test detection patterns"

# --- End LLM-Processor Service Commands ---

# --- TTS-Processor Service Commands ---

# Check TTS-processor service health
tts-health: check_docker
	@echo "---> Checking TTS-processor service health..."
	@if ! docker compose ps tts-processor | grep -q "Up"; then \
		echo "ERROR: TTS-processor container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@if [ -f .env ]; then \
		TTS_PORT=$$(grep -E '^[[:space:]]*TTS_PROCESSOR_HOST_PORT=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//'); \
		[ -z "$$TTS_PORT" ] && TTS_PORT=8125; \
		echo "---> TTS-processor health check:"; \
		curl -f http://localhost:$$TTS_PORT/health 2>/dev/null || echo "Health check failed"; \
	else \
		echo "---> TTS-processor health check:"; \
		curl -f http://localhost:8125/health 2>/dev/null || echo "Health check failed"; \
	fi

# Show TTS-processor service logs
tts-logs:
	@echo "---> Showing TTS-processor service logs..."
	@docker compose logs -f tts-processor

# Test TTS-processor generation endpoint
tts-test: check_docker
	@echo "---> Testing TTS-processor generation endpoint..."
	@if ! docker compose ps tts-processor | grep -q "Up"; then \
		echo "ERROR: TTS-processor container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@if [ -f .env ]; then \
		TTS_PORT=$$(grep -E '^[[:space:]]*TTS_PROCESSOR_HOST_PORT=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//'); \
		[ -z "$$TTS_PORT" ] && TTS_PORT=8125; \
		echo "---> Testing generation endpoint at http://localhost:$$TTS_PORT/generate"; \
		curl -X POST http://localhost:$$TTS_PORT/generate \
			-H "Content-Type: application/json" \
			-d '{"text": "Hello, this is a test of the TTS system!", "language": "en"}' 2>/dev/null || echo "TTS generation test failed"; \
	else \
		echo "---> Testing generation endpoint at http://localhost:8125/generate"; \
		curl -X POST http://localhost:8125/generate \
			-H "Content-Type: application/json" \
			-d '{"text": "Hello, this is a test of the TTS system!", "language": "en"}' 2>/dev/null || echo "TTS generation test failed"; \
	fi

# Monitor Redis streams related to TTS-processor
tts-streams: check_docker
	@echo "---> Monitoring TTS-processor Redis streams..."
	@if ! docker compose ps redis | grep -q "Up"; then \
		echo "ERROR: Redis container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@echo "---> Checking llm_responses stream (TTS input):"
	@docker compose exec -T redis redis-cli XINFO STREAM llm_responses 2>/dev/null || echo "Stream llm_responses not found"
	@echo "---> Checking tts_audio_queue stream (TTS output):"
	@docker compose exec -T redis redis-cli XINFO STREAM tts_audio_queue 2>/dev/null || echo "Stream tts_audio_queue not found"
	@echo "---> Checking TTS consumer groups:"
	@docker compose exec -T redis redis-cli XINFO GROUPS llm_responses 2>/dev/null || echo "No consumer groups for llm_responses"
	@docker compose exec -T redis redis-cli XINFO GROUPS tts_audio_queue 2>/dev/null || echo "No consumer groups for tts_audio_queue"

# Get TTS-processor statistics
tts-stats: check_docker
	@echo "---> Getting TTS-processor statistics..."
	@if ! docker compose ps tts-processor | grep -q "Up"; then \
		echo "ERROR: TTS-processor container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@if [ -f .env ]; then \
		TTS_PORT=$$(grep -E '^[[:space:]]*TTS_PROCESSOR_HOST_PORT=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//'); \
		[ -z "$$TTS_PORT" ] && TTS_PORT=8125; \
		echo "---> TTS statistics at http://localhost:$$TTS_PORT/stats"; \
		curl -f http://localhost:$$TTS_PORT/stats 2>/dev/null || echo "Stats retrieval failed"; \
	else \
		echo "---> TTS statistics at http://localhost:8125/stats"; \
		curl -f http://localhost:8125/stats 2>/dev/null || echo "Stats retrieval failed"; \
	fi

# List available TTS engines
tts-engines: check_docker
	@echo "---> Listing available TTS engines..."
	@if ! docker compose ps tts-processor | grep -q "Up"; then \
		echo "ERROR: TTS-processor container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@if [ -f .env ]; then \
		TTS_PORT=$$(grep -E '^[[:space:]]*TTS_PROCESSOR_HOST_PORT=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//'); \
		[ -z "$$TTS_PORT" ] && TTS_PORT=8125; \
		echo "---> Available engines at http://localhost:$$TTS_PORT/engines"; \
		curl -f http://localhost:$$TTS_PORT/engines 2>/dev/null || echo "Engine list retrieval failed"; \
	else \
		echo "---> Available engines at http://localhost:8125/engines"; \
		curl -f http://localhost:8125/engines 2>/dev/null || echo "Engine list retrieval failed"; \
	fi

# Restart only the TTS-processor service
tts-restart: check_docker
	@echo "---> Restarting TTS-processor service..."
	@docker compose restart tts-processor
	@echo "---> TTS-processor service restarted."

# Test complete TTS pipeline (LLM → TTS)
tts-pipeline-test: check_docker
	@echo "---> Testing complete TTS pipeline (LLM → TTS)..."
	@if ! docker compose ps llm-processor | grep -q "Up"; then \
		echo "ERROR: LLM-processor container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@if ! docker compose ps tts-processor | grep -q "Up"; then \
		echo "ERROR: TTS-processor container is not running. Please run 'make up' first."; \
		exit 1; \
	fi
	@echo "1. Sending test message to hey_raven_commands stream..."
	@docker compose exec -T redis redis-cli XADD hey_raven_commands "*" payload '{"question":"Hello Raven, what time is it?","session_uid":"test-session","meeting_id":"test-meeting","timestamp":"2025-09-16T22:00:00Z","context":"Pipeline test"}' 2>/dev/null || echo "Failed to send test message"
	@echo "2. Wait 5 seconds for processing..."
	@sleep 5
	@echo "3. Checking for TTS output in tts_audio_queue stream..."
	@docker compose exec -T redis redis-cli XLEN tts_audio_queue 2>/dev/null || echo "Failed to check output stream"
	@echo "4. Monitor the pipeline with: make tts-streams"

# --- End TTS-Processor Service Commands ---
