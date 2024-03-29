---
title: 'Faster quick start - add business logic'
sidebar_label: 'Add business logic'
id: add-business-logic
keywords: [getting started, quick start, faster quick start, business logic, dataserver, event handler]
tags:
    - getting started
    - quick start
    - faster quick start
    - business logic
    - dataserver
    - event handler
---

We have a table; now we want to be able to see its content and create new entries.


### Data Server
A Data Server allows for reading of real-time data. You must define the Data Server in the file **alpha-dataserver.kts**.

```kotlin
dataServer {
    query("ALL_TRADES", TRADE)
}
```

### Event Handler
Next, we want to be able to insert rows into our table. For this, you need to define an Event Handler in the file **alpha-eventhandler.kts**.

```kotlin
eventHandler {

    eventHandler<Trade>(name = "TRADE_INSERT") {
        onCommit { event ->
            entityDb.insert(event.details)
            ack()
        }
    }

}
```
