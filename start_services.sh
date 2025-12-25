#!/bin/bash
#
# Document Organizer Services Manager
# Starts/restarts both the document_organizer and Streamlit UI services
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
ENV_FILE="${SCRIPT_DIR}/.env"
LOG_DIR="${SCRIPT_DIR}/logs"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"

# PID files
ORGANIZER_PID_FILE="${SCRIPT_DIR}/.organizer.pid"
STREAMLIT_PID_FILE="${SCRIPT_DIR}/.streamlit.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create logs directory if needed
mkdir -p "${LOG_DIR}"

# Check if virtual environment exists
check_venv() {
    if [ ! -d "${VENV_DIR}" ]; then
        log_warn "Virtual environment not found at ${VENV_DIR}"
        log_info "Creating virtual environment..."
        python3 -m venv "${VENV_DIR}"
        log_success "Virtual environment created"

        log_info "Installing dependencies..."
        source "${VENV_DIR}/bin/activate"
        pip install --upgrade pip > /dev/null 2>&1
        pip install -r "${SCRIPT_DIR}/requirements.txt"
        log_success "Dependencies installed"
    fi
}

# Activate virtual environment and load .env
activate_env() {
    log_info "Activating virtual environment..."
    source "${VENV_DIR}/bin/activate"
    log_success "Virtual environment activated"

    if [ -f "${ENV_FILE}" ]; then
        log_info "Loading environment variables from .env..."
        set -a
        source "${ENV_FILE}"
        set +a
        log_success "Environment variables loaded"
    else
        log_warn ".env file not found at ${ENV_FILE}"
        log_warn "Copy .env.example to .env and configure your settings"
    fi
}

# Stop a service by PID file
stop_service() {
    local pid_file="$1"
    local service_name="$2"

    if [ -f "${pid_file}" ]; then
        local pid=$(cat "${pid_file}")
        if ps -p "${pid}" > /dev/null 2>&1; then
            log_info "Stopping ${service_name} (PID: ${pid})..."
            kill "${pid}" 2>/dev/null || true
            sleep 2
            # Force kill if still running
            if ps -p "${pid}" > /dev/null 2>&1; then
                kill -9 "${pid}" 2>/dev/null || true
            fi
            log_success "${service_name} stopped"
        else
            log_warn "${service_name} PID file exists but process not running"
        fi
        rm -f "${pid_file}"
    fi
}

# Stop all services
stop_all() {
    log_info "Stopping all services..."
    stop_service "${ORGANIZER_PID_FILE}" "Document Organizer"
    stop_service "${STREAMLIT_PID_FILE}" "Streamlit UI"

    # Also kill any orphaned processes
    pkill -f "python.*document_organizer.py" 2>/dev/null || true
    pkill -f "streamlit run ui.py" 2>/dev/null || true

    log_success "All services stopped"
}

# Start document organizer service
start_organizer() {
    local mode="${1:-watch}"

    log_info "Starting Document Organizer (mode: ${mode})..."

    cd "${SCRIPT_DIR}"

    if [ "${mode}" == "preprocess" ]; then
        nohup python document_organizer.py --preprocess > "${LOG_DIR}/organizer.log" 2>&1 &
    else
        nohup python document_organizer.py > "${LOG_DIR}/organizer.log" 2>&1 &
    fi

    local pid=$!
    echo "${pid}" > "${ORGANIZER_PID_FILE}"

    sleep 2
    if ps -p "${pid}" > /dev/null 2>&1; then
        log_success "Document Organizer started (PID: ${pid})"
        log_info "Log file: ${LOG_DIR}/organizer.log"
    else
        log_error "Document Organizer failed to start. Check ${LOG_DIR}/organizer.log"
        return 1
    fi
}

# Start Streamlit UI service
start_streamlit() {
    log_info "Starting Streamlit UI on port ${STREAMLIT_PORT}..."

    cd "${SCRIPT_DIR}"

    nohup streamlit run ui.py \
        --server.port="${STREAMLIT_PORT}" \
        --server.address="0.0.0.0" \
        --server.headless=true \
        > "${LOG_DIR}/streamlit.log" 2>&1 &

    local pid=$!
    echo "${pid}" > "${STREAMLIT_PID_FILE}"

    # Wait for Streamlit to start
    local retries=10
    while [ ${retries} -gt 0 ]; do
        if curl -s "http://localhost:${STREAMLIT_PORT}" > /dev/null 2>&1; then
            break
        fi
        sleep 1
        retries=$((retries - 1))
    done

    if ps -p "${pid}" > /dev/null 2>&1; then
        log_success "Streamlit UI started (PID: ${pid})"
        log_info "Access at: http://localhost:${STREAMLIT_PORT}"
        log_info "Log file: ${LOG_DIR}/streamlit.log"
    else
        log_error "Streamlit UI failed to start. Check ${LOG_DIR}/streamlit.log"
        return 1
    fi
}

# Show status of services
show_status() {
    echo ""
    echo "=== Service Status ==="

    if [ -f "${ORGANIZER_PID_FILE}" ] && ps -p "$(cat "${ORGANIZER_PID_FILE}")" > /dev/null 2>&1; then
        echo -e "Document Organizer: ${GREEN}Running${NC} (PID: $(cat "${ORGANIZER_PID_FILE}"))"
    else
        echo -e "Document Organizer: ${RED}Stopped${NC}"
    fi

    if [ -f "${STREAMLIT_PID_FILE}" ] && ps -p "$(cat "${STREAMLIT_PID_FILE}")" > /dev/null 2>&1; then
        echo -e "Streamlit UI:       ${GREEN}Running${NC} (PID: $(cat "${STREAMLIT_PID_FILE}")) - http://localhost:${STREAMLIT_PORT}"
    else
        echo -e "Streamlit UI:       ${RED}Stopped${NC}"
    fi

    echo ""
}

# Show logs
show_logs() {
    local service="${1:-all}"

    if [ "${service}" == "organizer" ] || [ "${service}" == "all" ]; then
        if [ -f "${LOG_DIR}/organizer.log" ]; then
            echo "=== Document Organizer Logs ==="
            tail -50 "${LOG_DIR}/organizer.log"
        fi
    fi

    if [ "${service}" == "streamlit" ] || [ "${service}" == "all" ]; then
        if [ -f "${LOG_DIR}/streamlit.log" ]; then
            echo "=== Streamlit UI Logs ==="
            tail -50 "${LOG_DIR}/streamlit.log"
        fi
    fi
}

# Usage information
show_usage() {
    echo "Document Organizer Services Manager"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start           Start all services (default)"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  status          Show status of all services"
    echo "  logs [service]  Show logs (organizer|streamlit|all)"
    echo ""
    echo "Options:"
    echo "  --preprocess    Run organizer in preprocess mode (extract+analyze only)"
    echo "  --port PORT     Set Streamlit port (default: 8501)"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start all services"
    echo "  $0 start --preprocess       # Start with organizer in preprocess mode"
    echo "  $0 restart                  # Restart all services"
    echo "  $0 logs streamlit           # Show Streamlit logs"
    echo ""
}

# Parse arguments
COMMAND="${1:-start}"
ORGANIZER_MODE="watch"

shift || true

while [[ $# -gt 0 ]]; do
    case $1 in
        --preprocess)
            ORGANIZER_MODE="preprocess"
            shift
            ;;
        --port)
            STREAMLIT_PORT="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Main execution
case "${COMMAND}" in
    start)
        check_venv
        activate_env
        stop_all
        start_organizer "${ORGANIZER_MODE}"
        start_streamlit
        show_status
        ;;
    stop)
        stop_all
        show_status
        ;;
    restart)
        check_venv
        activate_env
        stop_all
        start_organizer "${ORGANIZER_MODE}"
        start_streamlit
        show_status
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "${1:-all}"
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        log_error "Unknown command: ${COMMAND}"
        show_usage
        exit 1
        ;;
esac
