import logging

import azure.functions as func

from azure.identity import DefaultAzureCredential
from azure.mgmt.keyvault.aio import KeyVaultManagementClient
from azure.mgmt.resource.subscriptions.models import Subscription


async def main(msg: func.QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))

    sub = Subscription.deserialize(msg.get_json())

    logging.info('Starting KeyVault purg task for subscription: %s', sub.display_name)

    credential = DefaultAzureCredential()
    client = KeyVaultManagementClient(credential=credential, subscription_id=sub.subscription_id)

    logging.info('Getting deleted KeyVaults...')

    async with client, credential:
        async for kv in client.vaults.list_deleted():
            logging.info('Purging keyvault: %s...', kv.name)
            poller = await client.vaults.begin_purge_deleted(kv.name, kv.properties.location)
            await poller.result()

    logging.info('Done.')
