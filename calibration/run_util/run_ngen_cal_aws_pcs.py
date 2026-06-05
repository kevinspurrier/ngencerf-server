import functools
import logging
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status

from calibration.enums import StatusEnum, SlurmCallbackStatusEnum
from calibration.models import CalibrationRun, ValidationRun, ForecastRun, ColdStartRun, VerificationRun
from calibration.models.base_run import BaseRun
from calibration.models.hindcast_run import HindcastRun
from calibration.run_util.run_common import set_job_status, run_generic_job_end_callback, finalize_calibration_after_callback, \
    finalize_validation_after_callback, finalize_forecast_after_callback, finalize_cold_start_after_callback, finalize_verification_after_callback, \
    finalize_hindcast_after_callback
from calibration.run_util.slurm_client import get_slurm_session, generate_slurm_jwt
from calibration.views.common import get_job_description

logger = logging.getLogger(__name__)

User = get_user_model()


def submit_job_to_slurm(run: BaseRun, owner: User, arguments: dict[str, str], stdout_file: str) -> None:
    """
    Submits a job to AWS PCS via slurmrestd OpenAPI.
    """
    job_description = get_job_description(run)
    url = urljoin(settings.SLURM_URL, "/slurm/v0.0.39/job/submit")
    
    # Construct an sbatch script that will run the job using the ngencerf-server prod docker container
    # The actual executable inside the container depends on the run type
    # For now, we will construct a generic script
    script_content = f"#!/bin/bash\n#SBATCH --job-name={job_description}\n#SBATCH --output={stdout_file}\n"
    script_content += f"\n# Example execution logic inside docker/enroot\n"
    script_content += f"echo 'Running {job_description}'\n"

    payload = {
        "script": script_content,
        "job": {
            "name": f"ngencerf-{run.id}",
            "tasks": int(arguments.get('nprocs', 1)),
            "environment": {
                "NGEN_CAL_DATA_PATH": "/ngencerf/data"
            }
        }
    }

    logger.info(f"Submitting AWS PCS slurmrestd job for {job_description} to {url}")
    
    # In a real environment, we would also include JWT or munge auth headers
    headers = {
        "Content-Type": "application/json",
        "X-SLURM-USER-NAME": owner.username,
        "X-SLURM-USER-TOKEN": generate_slurm_jwt()
    }
    
    session = get_slurm_session()
    response = session.post(url, json=payload, headers=headers)
    response.raise_for_status()

    slurm_response = response.json()
    run.slurm_job_id = slurm_response.get('job_id')
    run.save(update_fields=['slurm_job_id'])
    logger.info(f"{job_description} submitted successfully to AWS PCS! slurm_job_id: {run.slurm_job_id}")


def check_pcs_for_failure(run: BaseRun, slurm_status: SlurmCallbackStatusEnum) -> bool:
    """
    Checks the status of a job executed in AWS PCS environment and updates its status accordingly.
    """
    if slurm_status == SlurmCallbackStatusEnum.CANCELED:
        logger.error(f"{get_job_description(run)} was cancelled")
        set_job_status(run, StatusEnum.CANCELLED)
        return True
    elif slurm_status == SlurmCallbackStatusEnum.FAILED:
        logger.error(f"{get_job_description(run)} ending due to abnormal return code {slurm_status}")
        set_job_status(run, StatusEnum.FAILED)
        return True
    return False


run_calibration_job_callback_pcs = functools.partial(
    run_generic_job_end_callback, check_if_failed=check_pcs_for_failure, finalize_func=finalize_calibration_after_callback
)

run_validation_job_callback_pcs = functools.partial(
    run_generic_job_end_callback, check_if_failed=check_pcs_for_failure, finalize_func=finalize_validation_after_callback
)

run_cold_start_job_callback_pcs = functools.partial(
    run_generic_job_end_callback, check_if_failed=check_pcs_for_failure, finalize_func=finalize_cold_start_after_callback
)

run_forecast_job_callback_pcs = functools.partial(
    run_generic_job_end_callback, check_if_failed=check_pcs_for_failure, finalize_func=finalize_forecast_after_callback
)

run_hindcast_job_callback_pcs = functools.partial(
    run_generic_job_end_callback, check_if_failed=check_pcs_for_failure, finalize_func=finalize_hindcast_after_callback
)

run_verification_job_callback_pcs = functools.partial(
    run_generic_job_end_callback, check_if_failed=check_pcs_for_failure, finalize_func=finalize_verification_after_callback
)


def cancel_slurm_job(run: BaseRun) -> bool:
    """
    Cancel a running Slurm job by sending a cancellation request to slurmrestd.
    """
    job_description = get_job_description(run)
    logger.info(f"Cancelling AWS PCS slurm job {run.slurm_job_id} for {job_description}")

    url = urljoin(settings.SLURM_URL, f"/slurm/v0.0.39/job/{run.slurm_job_id}")
    
    headers = {
        "Content-Type": "application/json",
        "X-SLURM-USER-NAME": getattr(settings, 'SLURM_REST_USER', 'ec2-user'),
        "X-SLURM-USER-TOKEN": generate_slurm_jwt()
    }
    
    session = get_slurm_session()
    response = session.delete(url, headers=headers)
    
    if response.status_code == status.HTTP_404_NOT_FOUND:
        return False
        
    response.raise_for_status()

    logger.info(f"{job_description} - {run.slurm_job_id} cancelled successfully via AWS PCS")
    return True
