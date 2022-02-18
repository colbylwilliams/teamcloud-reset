import os
import datetime
import logging
import typing
import json

import azure.functions as func

from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.cosmos.aio.cosmos_client import CosmosClient
from azure.mgmt.cosmosdb.aio import CosmosDBManagementClient
from azure.mgmt.resource.subscriptions.aio import SubscriptionClient
from azure.mgmt.web.aio import WebSiteManagementClient


async def main(resettimer: func.TimerRequest, msgs: func.Out[typing.List[str]]) -> None:

    # Cron set to "0 0 8 * * 6" Saturday morning 8am UTC (12am Saturnday PT)

    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    if resettimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Reset timer trigger function ran at %s', utc_timestamp)

    svc_rg = os.environ['TEAMCLOUD_SVC_RESOURCE_GROUP']
    svc_sub_id = os.environ['TEAMCLOUD_SVC_SUBSCRIPTION']
    svc_cosmos = os.environ['TEAMCLOUD_SVC_COSMOS_DB']
    sub_prefix = os.environ['SUBSCRIPTION_FILTER_PREFIX']

    credential = DefaultAzureCredential()

    logging.info('Reseting the following subscriptions:')

    sub_msgs = []

    async with credential, SubscriptionClient(credential=credential) as client:
        async for sub in client.subscriptions.list():
            if sub.display_name.lower().startswith(sub_prefix) and not sub.subscription_id == svc_sub_id:
                logging.info('...%s (%s)', sub.display_name, sub.subscription_id)
                sub_msgs.append(json.dumps(sub.serialize(keep_readonly=True)))

    msgs.set(sub_msgs)

    logging.info('Reseting Cosmos DB...')

    async with credential, CosmosDBManagementClient(credential=credential, subscription_id=svc_sub_id) as client:
        logging.info('...getting Cosmos account')
        cosmos_account = await client.database_accounts.get(svc_rg, svc_cosmos)
        logging.info('...getting Cosmos account keys')
        cosmos_keys = await client.database_accounts.list_keys(svc_rg, cosmos_account.name)

    async with CosmosClient(cosmos_account.document_endpoint, cosmos_keys.primary_master_key) as client:
        logging.info('...getting Cosmos databases')
        async for database in client.list_databases():
            try:
                logging.info('...deleting database with id: %s', database['id'])
                await client.delete_database(database)

            except CosmosResourceNotFoundError:
                logging.info('A database with id %s does not exist', database['id'])

    logging.info('Restarting apps...')

    async with credential, WebSiteManagementClient(credential=credential, subscription_id=svc_sub_id) as client:
        logging.info('...getting apps to restart')
        async for app in client.web_apps.list_by_resource_group(svc_rg):
            logging.info('...restarting %s', app.name)
            await client.web_apps.restart(app.resource_group, app.name)

    logging.info('Done.')
