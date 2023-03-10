---
title: 'Event Handler - advanced'
sidebar_label: 'Advanced'
id: advanced
keywords: [server, event handler, advanced]
tags:
  - server
  - event handler
  - advanced
---



## Custom reply message type
If you use a custom reply message type, you won’t be able to use the default `ack()` or `validationAck()` functions.  The custom message type needs to be returned from the method.

For a custom message type called `TradeEvent` defined as:

```kotlin
data class TradeEvent(
    val price: Double,
    val quantity: Int,
){
    init{
        require(price > 0) { "Price cannot be negative "}
        require(quantity > 0) { "Quantity cannot be negative "}
    }
}
```

...and a custom message reply type called `CustomTradeEventReply` defined as:

```kotlin
sealed class CustomTradeEventReply : Outbound() {
    class TradeEventValidateAck : CustomTradeEventReply()
    data class TradeEventAck(val tradeId: String) : CustomTradeEventReply()
    data class TradeEventNack(val error: String) : CustomTradeEventReply()
}
```

Add `CustomTradeEventReply` under **{app-name}-messages** and assemble. Once you have built, add `api(project(":alpha-messages"))` to your build.gradle.kts file under **{app-name}-script-config/build.gradle.kts**.

...you can now use the following example Event Handler below:

```kotlin
    eventHandler<TradeEvent, CustomTradeEventReply>(name = "CUSTOM_TRADE_EVENT") {
        onException { event, throwable ->
            CustomTradeEventReply.TradeEventNack(throwable.message!!)
        }
        onValidate {
            val tradeEvent = it.details
            val notional = tradeEvent.price?.times(tradeEvent.quantity!!.toDouble())
            
            require(notional!! < 1_000_000) { "Trade notional is too high" }
            CustomTradeEventReply.TradeEventValidateAck()
        }
        onCommit { event ->
            val trade = event.details
            val result = entityDb.insert(trade)
            CustomTradeEventReply.TradeEventAck(result.record.tradeId)
        }
    }
```

The following code assumes you have built your fields and tables after you created your `TradeEvent` under **jvm/{app-name}-config** with a primary key of `tradeId`. If intelliJ can't find you `TradeEvent`, go back and build your fields and tables as per the [Data Model Training](../../../getting-started/learn-the-basics/data-model/).

### onException

The `onException` block can capture any exceptions thrown by the `onValidate` and `onCommit` blocks and returns the expected reply message type (as shown in the last example). This function is particularly useful if you are using a custom message type; by default, Event Handlers will attempt to translate exceptions automatically to an `EventNack` message, which might cause compatibility problems if you are using custom replies.

## Permissioning and permissionCodes

As with other GPAL files (e.g. Request Server and Data Server), you can use a `permissioning` block to define both dynamic permissions (AUTH) and fixed permissions (based on RIGHT_SUMMARY rights) on Event Handlers.

### Dynamic permissions
For Event Handlers you need to use any class as event message type instead of table/view, which is similar to custom request-replies.
In the below example we use a generated database entity called `Company` as message type of event `EVENT_AUTH_COMPANY_INSERT`

```kotlin
    eventHandler<Company>(name = "AUTH_COMPANY_INSERT") {
        permissioning {
            auth(mapName = "COMPANY"){
                field { companyName } 
            }
        }

        onCommit { event ->
            val company = event.details
            val result = entityDb.insert(company)
            ack(listOf(mapOf("VALUE" to result.record.companyId)))
        }
    }
```

If you use custom class instead of generated database entities as message-type of events, we recommend that you locate your classes within the messages module of your application. This is where we place all the custom message types for our application. You need to ensure that the _app-name_**-script-config** module has a dependency on the messages module.

```bash
    api(project(":{app-name}-messages"))
```

### Permission codes

```kotlin
    eventHandler<Company>(name = "AUTH_COMPANY_INSERT") {
        permissionCodes = listOf("INSERT_TRADE")
        onCommit { event ->
            val company = event.details
            val result = entityDb.insert(company)
            ack(listOf(mapOf("VALUE" to result.record.companyId)))
        }
    }
```

You can find out more details in our section on [authorisation](../../../server/access-control/authorisation-overview/).


## Auto auditing

If the Event Handler message type is a database-generated entity that is auditable, Genesis automatically creates an audit record to the corresponding audit table for each database write operation. The audit fields are filled with the following values:

* AUDIT_EVENT_TYPE: Event name
* AUDIT_EVENT_DATETIME: Autogenerated
* AUDIT_EVENT_TEXT: Optional “REASON” value sent as part of the event message
* AUDIT_EVENT_USER: Extracted from the event message

## Defining state machines

State machines, which define the conditions for moving from one state to another, are defined within your Event Handler files. See more details about these in the section on [Defining your state machines](../../../server/state-machine/introduction/).

## Pending approvals


The Genesis low-code platform has an in-built pending approval mechanism that can be used with Event Handlers. This is useful where particular events require a second user to approve them in order to take effect. Genesis Pending Approvals works with the concepts of “delayed” events and "4-eyes check". 


### Set an event to require approval

Any event can be marked to "require approval" as long as the `REQUIRES_APPROVAL` flag is set to `true` in the incoming message. 

To configure an event for a mandatory `REQUIRES_APPROVAL` flag check, either:

- Override the `requiresPendingApproval` method to `true` in the custom Event Handler definitions. 
or
- Set the `requiresPendingApproval` property to `true` in a GPAL Event Handler.

Here is an example of a custom Event Handler definition:

 
```kotlin
import global.genesis.commons.annotation.Module
import global.genesis.eventhandler.typed.async.AsyncValidatingEventHandler
import global.genesis.message.core.event.Event
import global.genesis.message.core.event.EventReply

@Module
class TestCompanyHandlerAsync : AsyncValidatingEventHandler<Company, EventReply> {
    // Override requiresPendingApproval here to make the "pending approval" flow mandatory.
    override fun requiresPendingApproval(): Boolean = true
    
    override suspend fun onValidate(message: Event<Company>): EventReply {
        val company = message.details
        // custom code block..
        return ack()
    }

    override suspend fun onCommit(message: Event<Company>): EventReply {
        val company = message.details
        // custom code block..
        return ack()
    }
}
```

or in a GPAL definition:

```kotlin

eventHandler {
    eventHandler<Company> {
        requiresPendingApproval = true
        onCommit { event ->
            val company = event.details
            // custom code block..
            ack()
        }
    }
}
```

Events submitted with a `REQUIRES_APPROVAL` flag set to true are validated as usual (i.e. the `onValidate` method is run) and, if the validation is successful, the “delayed” event is stored in the `APPROVAL` table in a JSON format. 


Assuming the event is inserting, updating or deleting a target database record, it is possible to have multiple `APPROVAL` records associated with a single database entity. Use the event `onValidate` method to check for pre-existing approvals against the entities related to the event if you need to ensure there is only one pending approval per record. 

The validate method can also be used to determine if the incoming event needs approval e.g. checking if a particular field has been amended, or checking the tier on an incoming EVENT_ADD_CLIENT. If it does, then you can add the `REQUIRES_APPROVAL` flag to the event message.

The `APPROVAL` record is keyed on an auto-generated `APPROVAL_ID` and does not have a direct link to the original record. You have to create a link by adding “approval entity” details to the payload returned on an event ack in the `onValidate` method. These details include the `ENTITY_TABLE` and `ENTITY_KEY`. This allows you to decide how to identify the original record (e.g. creating a compound key in the case of multi-field keys). When the approval entity details are provided, the platform creates a record in the `APPROVAL_ENTITY` table and populates it with the details provided, and the `APPROVAL_ID` of the `APPROVAL` record. There is also an `APPROVAL_ENTITY_COUNTER`, which is populated by the AUTH_CONSOLIDATOR process by default; this can be handy in order to easily know how many approvals are pending for a given entity.


```kotlin
    override suspend fun onValidate(message: Event<Company>): EventReply {
        val company = message.details
        // custom code block..
        return ack(listOf(mapOf("ENTITY_TABLE" to "COMPANY", "ENTITY_ID" to company.companyId)))
    }
```


In order to display pending approvals against the original record in the GUI, you can use the `APPROVAL_ENTITY` table to join to the `APPROVAL_ENTITY` records in a view. You can then display the information using a Data Server or Request Server. The details of the pending event are stored in json format.


**Example APPROVAL DB record**


```DbM
TIMESTAMP          2018-09-19 09:29:51.111951844              NANO_TIMESTAMP
APPROVAL_ID        000000000000002APLO1                       STRING
APPROVAL_KEY       8a178f41-24c6-4cb3-b4e0-1996ae59bcddA...   STRING
APPROVAL_MESSAGE   Please approve this amendment              STRING
APPROVAL_STATUS    PENDING                                    ENUM[PENDING APPROVED CANCELLED REJECTED_BY_USER REJECTED_BY_SERVICE]
DESTINATION        EEP_INTENT_SERVICE                         STRING
MESSAGE_TYPE       EVENT_OPS_INTENT                           STRING
EVENT_DETAILS      TRADE_ID = LCH20180917.18500000098 DE...   STRING
EVENT_MESSAGE      {"MESSAGE_TYPE":"EVENT_OPS_INTENT","VAL... STRING
USER_NAME          CdsTest                                    STRING
```

### Configuring allowed approvers

Once in the `APPROVAL` table, the pending event can be cancelled, rejected or accepted by sending the following event messages to GENESIS_CLUSTER: 

- EVENT_PENDING_APPROVAL_ACCEPT
- EVENT_PENDING_APPROVAL_CANCEL
- EVENT_PENDING_APPROVAL_REJECT

All messages accept a `REASON_CODE` in their metadata.

The platform ensures that users cannot approve their own events. Additional levels of control (e.g. based on user groups) can be added to the front end, to the event validate method, or can be specified in server-side configuration.

To configure the allowed approvers in a server-side configuration, you need to create a new xml file with the following content. You need to add the file name to the GENESIS_CLUSTER `<config></config>` element in the site-specific version of the **genesis-processes.xml**:

```xml
<genesisCluster>
    <preExpression>
        <![CDATA[

        ]]>
    </preExpression>

    <pendingApproval>
        <insertPendingApproval>
            <![CDATA[
               true
            ]]>
        </insertPendingApproval>
        <acceptPendingApproval>
            <![CDATA[
               true
            ]]>
        </acceptPendingApproval>
        <rejectPendingApproval>
            <![CDATA[
               true
            ]]>
        </rejectPendingApproval>
        <cancelPendingApproval>
            <![CDATA[
               true
            ]]>
        </cancelPendingApproval>
    </pendingApproval>
</genesisCluster>
```

You can replace the "true" return value with Groovy code in each `pendingApproval` block. The platform makes the following objects accessible to your code:

- `userName` - a string property containing the user name who triggered the event (insert, accept, reject or cancel).
- `db` - an RxDb property so you can access the database layer and do appropriate checks.
- `pendingApproval` - the pending approval record stored in the database (only available in accept, reject or cancel events).

With this xml configuration, you can look up the user's rights in the database and return `true` only if the necessary rights are in place. For example, if your system has the concept of internal and external users and you only want to allow internal users to accept pending events, then you could check your custom user "ACCESS_TYPE" field as follows:

```xml
        ...
        <acceptPendingApproval>
            <![CDATA[
               def searchRecord = new DbRecord("USER_ATTRIBUTES")
               def userAttributes = db.get(searchRecord, "USER_ATTRIBUTES_BY_USER_NAME")
               userAttributes?.getString("ACCESS_TYPE") == "INTERNAL"
            ]]>
        </acceptPendingApproval>
        ...
```
## Defining an Event Handler in GPAL

The following imports are automatically available inside GPAL Event Handlers:

```kotlin
import CodeBlock from '@theme/CodeBlock';
import Imports from '!!raw-loader!/examples/server/java/event-handlers/imports.java';

<CodeBlock className="language-java">{Imports}</CodeBlock>
```


### Automatic import

The following properties are automatically available inside GPAL Event Handlers:

```kotlin
val systemDefinition: SystemDefinitionService
val rxDb: RxDb
val entityDb: AsyncEntityDb
val metaData: MetaDataRegistry
val evaluatorPool: EvaluatorPool
val messageDelegator: MessageDelegator
val networkConfiguration: NetworkConfiguration
val serviceDetailProvider: ServiceDetailProvider
val genesisHFT: GenesisHFT
val injector: Injector
val clientConnectionsManager: ClientConnectionsManager
val typedEventManager: TypedEventManager
```

