import os
import datetime
import logging
import typing
import json

import azure.functions as func

from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.cosmos.aio.cosmos_client import CosmosClient
from azure.mgmt.resource.subscriptions.aio import SubscriptionClient


async def main(resettimer: func.TimerRequest, msgs: func.Out[typing.List[str]]) -> None:

    # Cron set to "0 0 8 * * 6" Saturday morning 8am UTC (12am Saturnday PT)

    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if resettimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Reset timer trigger function ran at %s', utc_timestamp)

    sub_prefix = os.environ['SUBSCRIPTION_FILTER_PREFIX']
    skip_suffix = os.environ['SUBSCRIPTION_SKIP_SUFFIX']

    credential = DefaultAzureCredential()
    client = SubscriptionClient(credential=credential)

    logging.info('Reseting the following subscriptions:')

    sub_msgs = []

    async with client, credential:
        async for sub in client.subscriptions.list():
            if sub.display_name.lower().startswith(sub_prefix) and not sub.display_name.lower().endswith(skip_suffix):
                logging.info('...%s (%s)', sub.display_name, sub.subscription_id)
                sub_msgs.append(json.dumps(sub.serialize(keep_readonly=True)))

    msgs.set(sub_msgs)

    cosmos_url = os.environ['TEAMCLOUD_SVC_COSMOS_URL']
    cosmos_key = os.environ['TEAMCLOUD_SVC_COSMOS_KEY']

    logging.info('Reseting demo databases...')

    async with CosmosClient(cosmos_url, cosmos_key) as client:
        logging.info('Getting Cosmos databases...')
        async for database in client.list_databases():
            try:
                logging.info('Deleting database with id: %s', database['id'])
                await client.delete_database(database)

            except CosmosResourceNotFoundError:
                logging.info('A database with id %s does not exist', database['id'])

    logging.info('Done.')
