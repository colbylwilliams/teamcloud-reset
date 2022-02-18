import logging

import azure.functions as func

from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.keyvault.aio import KeyVaultManagementClient
from azure.mgmt.resource.subscriptions.models import Subscription


async def main(msg: func.QueueMessage) -> None:

    sub = Subscription.deserialize(msg.get_json())

    logging.info('Starting KeyVault purge task for subscription: %s', sub.display_name)

    credential = DefaultAzureCredential()

    logging.info('Getting deleted KeyVaults...')

    async with credential, KeyVaultManagementClient(credential=credential, subscription_id=sub.subscription_id) as client:
        async for kv in client.vaults.list_deleted():
            logging.info('Purging keyvault: %s...', kv.name)
            poller = await client.vaults.begin_purge_deleted(kv.name, kv.properties.location)
            await poller.result()

    logging.info('Done.')
