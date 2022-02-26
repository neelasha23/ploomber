import os
from glob import glob
import zipfile
from pathlib import Path
from functools import wraps

import click
import requests

from ploomber.table import Table

HOST = "https://lawqhyo5gl.execute-api.us-east-1.amazonaws.com/api/"


def auth_header(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = os.environ.get("PLOOMBER_CLOUD_KEY")

        if api_key:
            headers = {
                "Authorization": api_key,
                "Content-Type": "application/json"
            }

            return func(headers, *args, **kwargs)

    return wrapper


@auth_header
def runs_new(headers, task_names):
    return requests.post(f"{HOST}/runs/new",
                         headers=headers,
                         json=list(task_names)).json()


@auth_header
def runs(headers):
    res = requests.get(f"{HOST}/runs", headers=headers).json()
    print(Table.from_dicts(res))


# NOTE: this doesn't need authentication
def tasks_update(task_id, status):
    response = requests.get(f"{HOST}/tasks/{task_id}/{status}")
    json_ = response.json()

    if response.status_code >= 300:
        print(
            f'Failed to update task (status: {response.status_code}): {json_}')
    else:
        print(
            f'Successfully updated task (status: {response.status_code}): {json_}'
        )

    return json_


@auth_header
def run_detail(headers, run_id):
    res = requests.get(f"{HOST}/runs/{run_id}", headers=headers).json()
    print(Table.from_dicts(res['tasks']))


@auth_header
def products_list(headers):
    res = requests.get(f"{HOST}/products", headers=headers).json()

    if res:
        print(Table.from_dicts(res))
    else:
        print("No products found.")


@auth_header
def products_download(headers, pattern):
    return requests.get(f"{HOST}/products/{pattern}", headers=headers).json()


def zip_project():
    if Path("project.zip").exists():
        click.secho("Deleting existing project.zip...", fg="yellow")
        Path("project.zip").unlink()

    files = glob("**/*", recursive=True)

    # TODO: ignore __pycache__, ignore .git directory
    with zipfile.ZipFile("project.zip", "w", zipfile.ZIP_DEFLATED) as zip:
        for path in files:
            zip.write(path, arcname=path)


@auth_header
def get_presigned_link(headers):
    return requests.get(f"{HOST}/upload", headers=headers).json()


def upload_zipped_project(response):
    with open("project.zip", "rb") as f:
        files = {"file": f}
        http_response = requests.post(response["url"],
                                      data=response["fields"],
                                      files=files)

    if http_response.status_code != 204:
        raise ValueError(f"An error happened: {http_response}")

    click.secho("Uploaded project, starting execution...", fg="green")


def upload_project():
    if not Path("requirements.lock.txt").exists():
        raise ValueError("missing requirements.lock.txt")

    click.echo("Zipping project...")
    zip_project()
    click.echo("Uploading project...")
    response = get_presigned_link()
    upload_zipped_project(response)
