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

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    sub_prefix = os.environ['SUBSCRIPTION_FILTER_PREFIX']
    skip_suffix = os.environ['SUBSCRIPTION_SKIP_SUFFIX']

    credential = DefaultAzureCredential(logging_enable=True)
    client = SubscriptionClient(credential=credential)

    async with client, credential:
        subs = [sub async for sub in client.subscriptions.list()
                if sub.display_name.lower().startswith(sub_prefix)
                and not sub.display_name.lower().endswith(skip_suffix)]

    logging.info('Reseting the following subscriptions:')

    for sub in subs:
        logging.info('...%s (%s)', sub.display_name, sub.subscription_id)

    sub_msgs = [json.dumps(sub.serialize(keep_readonly=True)) for sub in subs]

    msgs.set(sub_msgs)

    cosmos_url = os.environ['TEAMCLOUD_SVC_COSMOS_URL']
    cosmos_key = os.environ['TEAMCLOUD_SVC_COSMOS_KEY']

    logging.info('Reseting demo databases...')

    async with CosmosClient(cosmos_url, cosmos_key) as client:
        logging.info('Getting Cosmos databases...')
        async for database in client.list_databases():
            try:
                logging.info('Deleting database with id: %s', database['id'])
                await client.delete_database(id)

            except CosmosResourceNotFoundError:
                logging.info('A database with id %s does not exist', database['id'])

    logging.info('Done.')
