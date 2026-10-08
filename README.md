# Moore Lab Fish Room @ University of Nebraska
Powered by the Coral Vue Hydros API, this repo creates a simple dashboard to display sensor information.  Check back for more updates!

Site can be visited at: [https://mgrapin55.github.io/MooreLabHydrosDashboard/](https://mgrapin55.github.io/MooreLabHydrosDashboard/)

## Standalone Hydros TSV logger

`backend/HydrosWriter.py` fetches Hydros sensor log data and appends one row per
reading to a dated TSV file. It uses only the Python standard libraries.

Set the two required credentials in the shell before running it:

```shell
export HYDROS_PROVIDER_KEY="your-provider-key"
export HYDROS_DEVICE_KEY="your-device-key"
python .\backend\HydrosWriter.py
```

Each run requests the previous complete UTC calendar month at `1d` resolution.
For example, an October run fetches September 1 up to (but not including)
October 1. It writes to
`backend/data/MooreLab.Call.YYYY-MM.tsv` using the month being collected, and
removes matching TSV files older than 365 days. Optional settings are
`HYDROS_OUTPUT_DIR`, `HYDROS_EXPIRATION_DAYS`, and `HYDROS_URL`. Schedule the
script to run once a month with a cron job, after the previous month has completed.
Set `HYDROS_RESOLUTION` to `1d`, `2h`, or `10m` to choose the log resolution;
the script checks the API response matches the requested resolution and records
it in each TSV row. Re-running for the same month replaces that month's file
instead of duplicating its readings.

### Running with Slurm

Copy `backend/.hydros.env.example` to `backend/.hydros.env`, add the API keys,
and keep the credentials file private. Maker ```error``` and ```out``` directories and  submit the batch job from the `backend`
directory so Slurm writes its output and error logs there:

```bash
cp .hydros.env.example .hydros.env
chmod 640 .hydros.env
mkdir -p error out
sbatch hydros-writer.sh
```

The batch script assumes `python3` is available on the compute node. Add your
cluster's required `--account` or `--partition` options to
`backend/hydros-writer.sh` if needed.   

Set the time you want to run the script again with ```sbatch --begin=now+30days hydros-writer.sh``` at the end of ```hydros-writer.sh```.