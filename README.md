# TeamCloud Reset

A solution that resets the TeamCloud demo instance weekly.

```mermaid
sequenceDiagram
    participant ResetTrigger
    participant ResetSubscriptionTrigger
    participant reset_subscription_queue
    participant delete_resourcegroup_queue
    participant DeleteResourceGroupTrigger
    participant ARM
    Note over ResetTrigger: Saturday morning 8am UTC
    ResetTrigger ->> ARM: GET subscriptions
    ARM -->> ResetTrigger: [subscriptions]
    ResetTrigger ->> reset_subscription_queue: [subscriptions]
    loop foreach subscription
        ResetSubscriptionTrigger ->> reset_subscription_queue: GET subscription
        reset_subscription_queue -->> ResetSubscriptionTrigger: {subscription}
        ResetSubscriptionTrigger ->> ARM: GET resource groups
        ARM -->> ResetSubscriptionTrigger: [resource groups]
        ResetSubscriptionTrigger ->> delete_resourcegroup_queue: [resource groups]
        loop foreach resource group
            DeleteResourceGroupTrigger ->> delete_resourcegroup_queue: GET resource group
            delete_resourcegroup_queue -->> DeleteResourceGroupTrigger: {resource group}
            DeleteResourceGroupTrigger ->> ARM: DELETE resource group
        end
    end
    ResetTrigger ->> ARM: DELETE TeamCloud and TeamCloudCache databases
    ResetTrigger ->> ARM: RESTART webapp
```

```mermaid
sequenceDiagram
    participant RefreshTrigger
    participant purge_keyvaults_queue
    participant PurgeKeyVaultsTrigger
    participant ARM
    Note over RefreshTrigger: Monday morning 5am UTC
    RefreshTrigger ->> ARM: GET subscriptions
    ARM -->> RefreshTrigger: [subscriptions]
    RefreshTrigger ->> purge_keyvaults_queue: [subscriptions]
    loop foreach subscription
        PurgeKeyVaultsTrigger ->> purge_keyvaults_queue: GET subscription
        purge_keyvaults_queue -->> PurgeKeyVaultsTrigger: {subscription}
        PurgeKeyVaultsTrigger ->> ARM: GET soft-deleted keyvaults for subscription
        ARM -->> PurgeKeyVaultsTrigger: [soft-deleted keyvaults]
        loop foreach soft-deleted keyvault
            PurgeKeyVaultsTrigger ->> ARM: purge keyvault
        end
    end
```

## Functions

The solution contains the following functions, in order of execution

#### `ResetTrigger`

- Triggered every Saturday morning 8am UTC to delete all resources created by the TeamCloud demo instance
- Gets a list of Subscription objects associated with the demo instance and adds them a queue named `reset-subscription-queue`
- Deletes the `TeamCloud` and `TeamCloudCache` databases from the demo instance's Cosmos account

#### `ResetSubscriptionTrigger`

- Triggered by new messages (Subscription objects) in the queue named `reset-subscription-queue`
- Gets a list of Resource Group objects for the Subscription and adds them to a queue named `delete-resourcegroup-queue`

#### `DeleteResourceGroupTrigger`

- Triggered by new messages (Resource Group objects) in the queue named `delete-resourcegroup-queue`
- Gets all the Locks on the Resource Group and it's resources and deletes them
- Deletes the Resource Group

#### `RefreshTrigger`

- Triggered every Monday morning 5am UTC to seed the TeamCloud demo instance
- Gets a list of Subscription objects associated with the demo instance and adds them a queue named `purge-keyvaults-queue`

#### `PurgeKeyVaultsTrigger`

- Triggered by new messages (Subscription objects) in the queue named `purge-keyvaults-queue`
- Gets a list of soft-deleted KeyVaults for the Subscription and purges (permanently deletes) them

## // TODO

- Seed the demo with a few Organizations, Deployment Scopes, Project Templates, Projects?
