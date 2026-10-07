#!/bin/bash
#SBATCH --job-name=hydros-writer
#SBATCH --time=00:10:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=512M
#SBATCH --output=hydros-writer-%j.out
#SBATCH --error=hydros-writer-%j.err
#SBATCH --partition=batch

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.hydros.env"

if [[ ! -f "${ENV_FILE}" ]]; then
    echo "Missing credentials file: ${ENV_FILE}" >&2
    echo "Copy .hydros.env.example to .hydros.env and add the API keys." >&2
    exit 1
fi

source "${ENV_FILE}"
cd "${SCRIPT_DIR}"
python3 HydrosWriter.py


# Remove old error and output slurm logs
find "$SCRIPT_DIR" -maxdepth 1 -type f \
  \( -name "hydros-writer-*.err" -o -name "hydros-writer-*.out" \) \
  -mtime +365 -delete
