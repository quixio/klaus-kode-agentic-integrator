The Slack Web API is an interface for querying information _from_ and enacting change _in_ a Slack workspace.

Use it for individual queries, or as part of a more complex tapestry of platform features in a [Slack app](https://api.slack.com/docs/apps).

When sending a HTTP POST, you may present your arguments as either standard POST parameters, or you may use JSON instead.

When sending URL-encoded data, set your HTTP `Content-type` header to `application/x-www-form-urlencoded` and present your key/value pairs according to [RFC-3986](https://tools.ietf.org/html/rfc3986).

For example, a POST request to the [`conversations.create`](https://api.slack.com/methods/conversations.create) method might look something like this:

For [write methods that support JSON](https://api.slack.com/web#methods_supporting_json), you may alternatively send your HTTP POST data as `Content-type: application/json`.

For example, to send the same request above to the `conversations.create` method with a JSON POST body, send something like this:

Note how we present the token with the string `Bearer` pre-pended to it, indicating the [OAuth 2.0](https://api.slack.com/authentication) authentication scheme. Consult your favorite HTTP tool or library's manual for further detail on setting HTTP headers.

Here's a more complicated example — posting a message with [menus](https://api.slack.com/docs/message-menus) using [`chat.postMessage`](https://api.slack.com/methods/chat.postMessage):

The `attachments` argument is sent a straightforward JSON array.

If the posted JSON is invalid, you'll receive one of the following errors in response:

In both cases, you'll need to revise your JSON or how you're transmitting your data to resolve the error condition.

All Web API responses contain a JSON object, which will always contain a top-level boolean property `ok` that indicates success or failure.

For failure results, the `error` property will contain a short machine-readable error code. In the case of problematic calls that could still be completed successfully, `ok` will be `true` and the `warning` property will contain a short machine-readable warning code (or comma-separated list of them, in the case of multiple warnings). See the following examples:

Other properties are defined in the documentation for each relevant method. There's a lot of "stuff" to unpack, including [these types](https://api.slack.com/types) and other method or domain-specific curiosities.

Authenticate your Web API requests by providing a [bearer token](https://api.slack.com/docs/token-types), which identifies a single user or bot user relationship.

[Register your application](https://api.slack.com/apps) with Slack to obtain credentials for use with our [OAuth 2.0](https://api.slack.com/authentication/oauth-v2) implementation, which allows you to negotiate tokens on behalf of users and workspaces.

We prefer tokens to be sent in the `Authorization` HTTP header of your outbound requests. However, you may also pass tokens in all Web API calls as a POST body parameter called `token`. Tokens cannot be sent as a query parameter.

All TLS connections must use the [SNI extension](https://en.wikipedia.org/wiki/Server_Name_Indication). Lastly, TLS connections must support at least one of the following cipher suites:

With over 100 methods, surely there's one right for you. Here is a list of the different method families available in our Web API:

These methods support sending `application/json` instead of `application/x-www-form-urlencoded` arguments.

|                                                                                       Method & Description                                                                                       |                                                                       Description                                                                       |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| admin.apps.approve

Approve an app for installation on a workspace. |                                                     Approve an app for installation on a workspace.                                                     |
| admin.apps.clearResolution

Clear an app resolution |                                                                 Clear an app resolution                                                                 |
| admin.apps.config.lookup

Look up the app config for connectors by their IDs |                                                   Look up the app config for connectors by their IDs                                                    |
| admin.apps.config.set

Set the app config for a connector |                                                           Set the app config for a connector                                                            |
| admin.apps.requests.cancel

Cancel app request for team |                                                               Cancel app request for team                                                               |
| admin.apps.restrict

Restrict an app for installation on a workspace. |                                                    Restrict an app for installation on a workspace.                                                     |
| admin.apps.uninstall

Uninstall an app from one or many workspaces, or an entire enterprise organization. |                                   Uninstall an app from one or many workspaces, or an entire enterprise organization.                                   |
| admin.audit.anomaly.allow.getItem

API to allow enterprise grid admins to read the allow list of IP blocks and ASNs from the enterprise configuration. |                   API to allow enterprise grid admins to read the allow list of IP blocks and ASNs from the enterprise configuration.                   |
| admin.audit.anomaly.allow.updateItem

API to allow enterprise grid admins to write/overwrite the allow list of IP blocks and ASNs from the enterprise configuration. |             API to allow enterprise grid admins to write/overwrite the allow list of IP blocks and ASNs from the enterprise configuration.              |
| admin.auth.policy.assignEntities

Assign entities to a particular authentication policy. |                                                 Assign entities to a particular authentication policy.                                                  |
| admin.auth.policy.getEntities

Fetch all the entities assigned to a particular authentication policy by name. |                                     Fetch all the entities assigned to a particular authentication policy by name.                                      |
| admin.auth.policy.removeEntities

Remove specified entities from a specified authentication policy. |                                            Remove specified entities from a specified authentication policy.                                            |
| admin.conversations.archive

Archive a public or private channel. |                                                          Archive a public or private channel.                                                           |
| admin.conversations.convertToPrivate

Convert a public channel to a private channel. |                                                     Convert a public channel to a private channel.                                                      |
| admin.conversations.convertToPublic

Convert a private channel to a public channel. |                                                     Convert a private channel to a public channel.                                                      |
| admin.conversations.create

Create a public or private channel-based conversation. |                                                 Create a public or private channel-based conversation.                                                  |
| admin.conversations.createForObjects

Create a Salesforce channel for the corresponding object provided. |                                           Create a Salesforce channel for the corresponding object provided.                                            |
| admin.conversations.delete

Delete a public or private channel. |                                                           Delete a public or private channel.                                                           |
| admin.conversations.disconnectShared

Disconnect a connected channel from one or more workspaces. |                                               Disconnect a connected channel from one or more workspaces.                                               |
| admin.conversations.getConversationPrefs

Get conversation preferences for a public or private channel. |                                              Get conversation preferences for a public or private channel.                                              |
| admin.conversations.getCustomRetention

This API endpoint can be used by any admin to get a conversation's retention policy. |                                  This API endpoint can be used by any admin to get a conversation's retention policy.                                   |
| admin.conversations.getTeams

Get all the workspaces a given public or private channel is connected to within this Enterprise org. |                          Get all the workspaces a given public or private channel is connected to within this Enterprise org.                           |
| admin.conversations.invite

Invite a user to a public or private channel. |                                                      Invite a user to a public or private channel.                                                      |
| admin.conversations.linkObjects

Link a Salesforce record to a channel |                                                          Link a Salesforce record to a channel                                                          |
| admin.conversations.removeCustomRetention

This API endpoint can be used by any admin to remove a conversation's retention policy. |                                 This API endpoint can be used by any admin to remove a conversation's retention policy.                                 |
| admin.conversations.rename

Rename a public or private channel. |                                                           Rename a public or private channel.                                                           |
| admin.conversations.search

Search for public or private channels in an Enterprise organization. |                                          Search for public or private channels in an Enterprise organization.                                           |
| admin.conversations.setConversationPrefs

Set the posting permissions for a public or private channel. |                                              Set the posting permissions for a public or private channel.                                               |
| admin.conversations.setCustomRetention

This API endpoint can be used by any admin to set a conversation's retention policy. |                                  This API endpoint can be used by any admin to set a conversation's retention policy.                                   |
| admin.conversations.setTeams

Set the workspaces in an Enterprise grid org that connect to a public or private channel. |                                Set the workspaces in an Enterprise grid org that connect to a public or private channel.                                |
| admin.conversations.unarchive

Unarchive a public or private channel. |                                                         Unarchive a public or private channel.                                                          |
| admin.conversations.unlinkObjects

Unlink a Salesforce record from a channel |                                                        Unlink a Salesforce record from a channel                                                        |
| admin.functions.list

Look up functions by a set of apps |                                                           Look up functions by a set of apps                                                            |
| admin.functions.permissions.lookup

Lookup the visibility of multiple Slack functions and include the users if it is limited to particular named entities. |                 Lookup the visibility of multiple Slack functions and include the users if it is limited to particular named entities.                  |
| admin.functions.permissions.set

Set the visibility of a Slack function and define the users or workspaces if it is set to named\_entities |                        Set the visibility of a Slack function and define the users or workspaces if it is set to named\_entities                        |
| admin.inviteRequests.approve

Approve a workspace invite request. |                                                           Approve a workspace invite request.                                                           |
| admin.inviteRequests.approved.list

List all approved workspace invite requests. |                                                      List all approved workspace invite requests.                                                       |
| admin.inviteRequests.denied.list

List all denied workspace invite requests. |                                                       List all denied workspace invite requests.                                                        |
| admin.inviteRequests.deny

Deny a workspace invite request. |                                                            Deny a workspace invite request.                                                             |
| admin.inviteRequests.list

List all pending workspace invite requests. |                                                       List all pending workspace invite requests.                                                       |
| admin.roles.addAssignments

Adds members to the specified role with the specified scopes |                                              Adds members to the specified role with the specified scopes                                               |
| admin.teams.create

Create an Enterprise team. |                                                               Create an Enterprise team.                                                                |
| admin.teams.list

List all teams on an Enterprise organization |                                                      List all teams on an Enterprise organization                                                       |
| admin.teams.settings.info

Fetch information about settings in a workspace |                                                     Fetch information about settings in a workspace                                                     |
| admin.teams.settings.setDescription

Set the description of a given workspace. |                                                        Set the description of a given workspace.                                                        |
| admin.teams.settings.setDiscoverability

An API method that allows admins to set the discoverability of a given workspace |                                    An API method that allows admins to set the discoverability of a given workspace                                     |
| admin.teams.settings.setName

Set the name of a given workspace. |                                                           Set the name of a given workspace.                                                            |
| admin.usergroups.addChannels

Add up to one hundred default channels to an IDP group. |                                                 Add up to one hundred default channels to an IDP group.                                                 |
| admin.usergroups.addTeams

Associate one or more default workspaces with an organization-wide IDP group. |                                      Associate one or more default workspaces with an organization-wide IDP group.                                      |
| admin.usergroups.listChannels

List the channels linked to an org-level IDP group (user group). |                                            List the channels linked to an org-level IDP group (user group).                                             |
| admin.usergroups.removeChannels

Remove one or more default channels from an org-level IDP group (user group). |                                      Remove one or more default channels from an org-level IDP group (user group).                                      |
| admin.users.assign

Add an Enterprise user to a workspace. |                                                         Add an Enterprise user to a workspace.                                                          |
| admin.users.invite

Invite a user to a workspace. |                                                              Invite a user to a workspace.                                                              |
| admin.users.list

List users on a workspace |                                                                List users on a workspace                                                                |
| admin.users.remove

Remove a user from a workspace. |                                                             Remove a user from a workspace.                                                             |
| admin.users.session.clearSettings

Clear user-specific session settings—the session duration and what happens when the client closes—for a list of users. |                 Clear user-specific session settings—the session duration and what happens when the client closes—for a list of users.                  |
| admin.users.session.getSettings

Get user-specific session settings—the session duration and what happens when the client closes—given a list of users. |                 Get user-specific session settings—the session duration and what happens when the client closes—given a list of users.                  |
| admin.users.session.invalidate

Revoke a single session for a user. The user will be forced to login to Slack. |                                     Revoke a single session for a user. The user will be forced to login to Slack.                                      |
| admin.users.session.list

List active user sessions for an organization |                                                      List active user sessions for an organization                                                      |
| admin.users.session.reset

Wipes all valid sessions on all devices for a given user |                                                Wipes all valid sessions on all devices for a given user                                                 |
| admin.users.session.resetBulk

Enqueues an asynchronous job to wipe all valid sessions on all devices for a given list of users |                            Enqueues an asynchronous job to wipe all valid sessions on all devices for a given list of users                             |
| admin.users.session.setSettings

Configure the user-level session settings—the session duration and what happens when the client closes—for one or more users. |              Configure the user-level session settings—the session duration and what happens when the client closes—for one or more users.              |
| admin.users.setAdmin

Set an existing regular user or owner to be a workspace admin. |                                             Set an existing regular user or owner to be a workspace admin.                                              |
| admin.users.setExpiration

Set an expiration for a guest user |                                                           Set an expiration for a guest user                                                            |
| admin.users.setOwner

Set an existing regular user or admin to be a workspace owner. |                                             Set an existing regular user or admin to be a workspace owner.                                              |
| admin.users.setRegular

Set an existing guest user, admin user, or owner to be a regular user. |                                         Set an existing guest user, admin user, or owner to be a regular user.                                          |
| admin.workflows.collaborators.add

Add collaborators to workflows within the team or enterprise |                                              Add collaborators to workflows within the team or enterprise                                               |
| admin.workflows.collaborators.remove

Remove collaborators from workflows within the team or enterprise |                                            Remove collaborators from workflows within the team or enterprise                                            |
| admin.workflows.permissions.lookup

Look up the permissions for a set of workflows |                                                     Look up the permissions for a set of workflows                                                      |
| admin.workflows.search

Search workflows within the team or enterprise |                                                     Search workflows within the team or enterprise                                                      |
| admin.workflows.triggers.types.permissions.lookup

list the permissions for using each trigger type |                                                    list the permissions for using each trigger type                                                     |
| admin.workflows.triggers.types.permissions.set

Set the permissions for using a trigger type |                                                      Set the permissions for using a trigger type                                                       |
| admin.workflows.unpublish

Unpublish workflows within the team or enterprise |                                                    Unpublish workflows within the team or enterprise                                                    |
| api.test

Checks API calling code. |                                                                Checks API calling code.                                                                 |
| apps.auth.external.delete

Delete external auth tokens only on the Slack side |                                                   Delete external auth tokens only on the Slack side                                                    |
| apps.auth.external.get

Get the access token for the provided token ID |                                                     Get the access token for the provided token ID                                                      |
| apps.connections.open

Generate a temporary Socket Mode WebSocket URL that your app can connect to in order to receive events and interactive payloads over. |          Generate a temporary Socket Mode WebSocket URL that your app can connect to in order to receive events and interactive payloads over.          |
| apps.datastore.bulkDelete

Delete items from a datastore in bulk |                                                          Delete items from a datastore in bulk                                                          |
| apps.datastore.bulkGet

Get items from a datastore in bulk |                                                           Get items from a datastore in bulk                                                            |
| apps.datastore.bulkPut

Creates or replaces existing items in bulk |                                                       Creates or replaces existing items in bulk                                                        |
| apps.datastore.count

Count the number of items in a datastore that match a query |                                               Count the number of items in a datastore that match a query                                               |
| apps.datastore.delete

Delete an item from a datastore |                                                             Delete an item from a datastore                                                             |
| apps.datastore.get

Get an item from a datastore |                                                              Get an item from a datastore                                                               |
| apps.datastore.put

Creates a new item, or replaces an old item with a new item. |                                              Creates a new item, or replaces an old item with a new item.                                               |
| apps.datastore.query

Query a datastore for items |                                                               Query a datastore for items                                                               |
| apps.datastore.update

Edits an existing item's attributes, or adds a new item if it does not already exist. |                                  Edits an existing item's attributes, or adds a new item if it does not already exist.                                  |
| apps.event.authorizations.list

Get a list of authorizations for the given event context. Each authorization represents an app installation that the event is visible to. |        Get a list of authorizations for the given event context. Each authorization represents an app installation that the event is visible to.        |
| apps.manifest.create

Create an app from an app manifest. |                                                           Create an app from an app manifest.                                                           |
| apps.manifest.delete

Permanently deletes an app created through app manifests |                                                Permanently deletes an app created through app manifests                                                 |
| apps.manifest.export

Export an app manifest from an existing app |                                                       Export an app manifest from an existing app                                                       |
| apps.manifest.update

Update an app from an app manifest |                                                           Update an app from an app manifest                                                            |
| apps.manifest.validate

Validate an app manifest |                                                                Validate an app manifest                                                                 |
| assistant.search.context

Searches messages across your Slack organization—perfect for broad, specific, and real-time data retrieval. |                       Searches messages across your Slack organization—perfect for broad, specific, and real-time data retrieval.                       |
| assistant.search.info

Returns search capabilities on a given team. |                                                      Returns search capabilities on a given team.                                                       |
| assistant.threads.setStatus

Set the status for an AI assistant thread. |                                                       Set the status for an AI assistant thread.                                                        |
| assistant.threads.setSuggestedPrompts

Set suggested prompts for the given assistant thread |                                                  Set suggested prompts for the given assistant thread                                                   |
| assistant.threads.setTitle

Set the title for the given assistant thread |                                                      Set the title for the given assistant thread                                                       |
| auth.test

Checks authentication & identity. |                                                            Checks authentication & identity.                                                            |
| bookmarks.add

Add bookmark to a channel. |                                                               Add bookmark to a channel.                                                                |
| bookmarks.edit

Edit bookmark. |                                                                     Edit bookmark.                                                                      |
| bookmarks.list

List bookmark for the channel. |                                                             List bookmark for the channel.                                                              |
| bookmarks.remove

Remove bookmark from the channel. |                                                            Remove bookmark from the channel.                                                            |
| calls.add

Registers a new Call. |                                                                  Registers a new Call.                                                                  |
| calls.end

Ends a Call. |                                                                      Ends a Call.                                                                       |
| calls.info

Returns information about a Call. |                                                            Returns information about a Call.                                                            |
| calls.participants.add

Registers new participants added to a Call. |                                                       Registers new participants added to a Call.                                                       |
| calls.participants.remove

Registers participants removed from a Call. |                                                       Registers participants removed from a Call.                                                       |
| calls.update

Updates information about a Call. |                                                            Updates information about a Call.                                                            |
| canvases.access.delete

Remove access to a canvas for specified entities |                                                    Remove access to a canvas for specified entities                                                     |
| canvases.access.set

Sets the access level to a canvas for specified entities |                                                Sets the access level to a canvas for specified entities                                                 |
| canvases.create

Create canvas for a user |                                                                Create canvas for a user                                                                 |
| canvases.delete

Deletes a canvas |                                                                    Deletes a canvas                                                                     |
| canvases.edit

Update an existing canvas |                                                                Update an existing canvas                                                                |
| canvases.sections.lookup

Find sections matching the provided criteria |                                                      Find sections matching the provided criteria                                                       |
| channels.mark

Sets the read cursor in a channel. |                                                           Sets the read cursor in a channel.                                                            |
| chat.delete

Deletes a message. |                                                                   Deletes a message.                                                                    |
| chat.deleteScheduledMessage

Deletes a pending scheduled message from the queue. |                                                   Deletes a pending scheduled message from the queue.                                                   |
| chat.meMessage

Share a me message into a channel. |                                                           Share a me message into a channel.                                                            |
| chat.postEphemeral

Sends an ephemeral message to a user in a channel. |                                                   Sends an ephemeral message to a user in a channel.                                                    |
| chat.postMessage

Sends a message to a channel. |                                                              Sends a message to a channel.                                                              |
| chat.scheduleMessage

Schedules a message to be sent to a channel. |                                                      Schedules a message to be sent to a channel.                                                       |
| chat.scheduledMessages.list

Returns a list of scheduled messages. |                                                          Returns a list of scheduled messages.                                                          |
| chat.unfurl

Provide custom unfurl behavior for user-posted URLs |                                                   Provide custom unfurl behavior for user-posted URLs                                                   |
| chat.update

Updates a message. |                                                                   Updates a message.                                                                    |
| conversations.acceptSharedInvite

Accepts an invitation to a Slack Connect channel. |                                                    Accepts an invitation to a Slack Connect channel.                                                    |
| conversations.approveSharedInvite

Approves an invitation to a Slack Connect channel |                                                    Approves an invitation to a Slack Connect channel                                                    |
| conversations.archive

Archives a conversation. |                                                                Archives a conversation.                                                                 |
| conversations.canvases.create

Create a channel canvas for a channel |                                                          Create a channel canvas for a channel                                                          |
| conversations.close

Closes a direct message or multi-person direct message. |                                                 Closes a direct message or multi-person direct message.                                                 |
| conversations.create

Initiates a public or private channel-based conversation |                                                Initiates a public or private channel-based conversation                                                 |
| conversations.declineSharedInvite

Declines a Slack Connect channel invite. |                                                        Declines a Slack Connect channel invite.                                                         |
| conversations.history

Fetches a conversation's history of messages and events. |                                                Fetches a conversation's history of messages and events.                                                 |
| conversations.invite

Invites users to a channel. |                                                               Invites users to a channel.                                                               |
| conversations.inviteShared

Sends an invitation to a Slack Connect channel |                                                     Sends an invitation to a Slack Connect channel                                                      |
| conversations.join

Joins an existing conversation. |                                                             Joins an existing conversation.                                                             |
| conversations.kick

Removes a user from a conversation. |                                                           Removes a user from a conversation.                                                           |
| conversations.leave

Leaves a conversation. |                                                                 Leaves a conversation.                                                                  |
| conversations.listConnectInvites

Lists shared channel invites that have been generated or received but have not been approved by all parties |                       Lists shared channel invites that have been generated or received but have not been approved by all parties                       |
| conversations.mark

Sets the read cursor in a channel. |                                                           Sets the read cursor in a channel.                                                            |
| conversations.open

Opens or resumes a direct message or multi-person direct message. |                                            Opens or resumes a direct message or multi-person direct message.                                            |
| conversations.rename

Renames a conversation. |                                                                 Renames a conversation.                                                                 |
| conversations.requestSharedInvite.approve

Approves a request to add an external user to a channel and sends them a Slack Connect invite |                              Approves a request to add an external user to a channel and sends them a Slack Connect invite                              |
| conversations.requestSharedInvite.deny

Denies a request to invite an external user to a channel |                                                Denies a request to invite an external user to a channel                                                 |
| conversations.requestSharedInvite.list

Lists requests to add external users to channels with ability to filter. |                                        Lists requests to add external users to channels with ability to filter.                                         |
| conversations.setPurpose

Sets the channel description. |                                                              Sets the channel description.                                                              |
| conversations.setTopic

Sets the topic for a conversation. |                                                           Sets the topic for a conversation.                                                            |
| conversations.unarchive

Reverses conversation archival. |                                                             Reverses conversation archival.                                                             |
| dialog.open

Open a dialog with a user |                                                                Open a dialog with a user                                                                |
| dnd.endDnd

Ends the current user's Do Not Disturb session immediately. |                                               Ends the current user's Do Not Disturb session immediately.                                               |
| dnd.endSnooze

Ends the current user's snooze mode immediately. |                                                    Ends the current user's snooze mode immediately.                                                     |
| dnd.setSnooze

Turns on Do Not Disturb mode for the current user, or changes its duration. |                                       Turns on Do Not Disturb mode for the current user, or changes its duration.                                       |
| files.comments.delete

Deletes an existing comment on a file. |                                                         Deletes an existing comment on a file.                                                          |
| files.completeUploadExternal

Finishes an upload started with files.getUploadURLExternal |                                               Finishes an upload started with files.getUploadURLExternal                                                |
| files.delete

Deletes a file. |                                                                     Deletes a file.                                                                     |
| files.revokePublicURL

Revokes public/external sharing access for a file |                                                    Revokes public/external sharing access for a file                                                    |
| files.sharedPublicURL

Enables a file for public/external sharing. |                                                       Enables a file for public/external sharing.                                                       |
| functions.completeError

Signal that a function failed to complete |                                                        Signal that a function failed to complete                                                        |
| functions.completeSuccess

Signal the successful completion of a function |                                                     Signal the successful completion of a function                                                      |
| functions.distributions.permissions.add

Grant users access to a custom slack function if its permission\_type is set to named\_entities |                              Grant users access to a custom slack function if its permission\_type is set to named\_entities                              |
| functions.distributions.permissions.list

List the access type of a custom slack function and include the users or team or org ids with access if its permission\_type is set to named\_entities |  List the access type of a custom slack function and include the users or team or org ids with access if its permission\_type is set to named\_entities   |
| functions.distributions.permissions.remove

Revoke user access to a custom slack function if permission\_type set to named\_entities |                                 Revoke user access to a custom slack function if permission\_type set to named\_entities                                  |
| functions.distributions.permissions.set

Set the access type of a custom slack function and define the users or team or org ids to be granted access if permission\_type is set to named\_entities | Set the access type of a custom slack function and define the users or team or org ids to be granted access if permission\_type is set to named\_entities |
| functions.workflows.steps.list

List the steps of a specific function of a workflow's versions |                                             List the steps of a specific function of a workflow's versions                                              |
| functions.workflows.steps.responses.export

Download form responses of a workflow |                                                          Download form responses of a workflow                                                          |
| groups.mark

Sets the read cursor in a private channel. |                                                       Sets the read cursor in a private channel.                                                        |
| im.mark

Sets the read cursor in a direct message channel. |                                                    Sets the read cursor in a direct message channel.                                                    |
| mpim.mark

Sets the read cursor in a multiparty direct message channel. |                                              Sets the read cursor in a multiparty direct message channel.                                               |
| pins.add

Pins an item to a channel. |                                                               Pins an item to a channel.                                                                |
| pins.remove

Un-pins an item from a channel. |                                                             Un-pins an item from a channel.                                                             |
| reactions.add

Adds a reaction to an item. |                                                               Adds a reaction to an item.                                                               |
| reactions.remove

Removes a reaction from an item. |                                                            Removes a reaction from an item.                                                             |
| reminders.add

Creates a reminder. |                                                                   Creates a reminder.                                                                   |
| reminders.complete

Marks a reminder as complete. |                                                              Marks a reminder as complete.                                                              |
| reminders.delete

Deletes a reminder. |                                                                   Deletes a reminder.                                                                   |
| slackLists.access.delete

Remove access to a list for specified entities |                                                     Remove access to a list for specified entities                                                      |
| slackLists.access.set

Sets the access level to a list for specified entities |                                                 Sets the access level to a list for specified entities                                                  |
| slackLists.create

Create a list |                                                                      Create a list                                                                      |
| slackLists.download.get

Retrieve list download URL from an export job to download list contents |                                         Retrieve list download URL from an export job to download list contents                                         |
| slackLists.download.start

Initiate a job to export list contents |                                                         Initiate a job to export list contents                                                          |
| slackLists.items.create

Adds a new item to an existing list. |                                                          Adds a new item to an existing list.                                                           |
| slackLists.items.delete

Deletes an item from an existing list. |                                                         Deletes an item from an existing list.                                                          |
| slackLists.items.deleteMultiple

Deletes multiple items from an existing list. |                                                      Deletes multiple items from an existing list.                                                      |
| slackLists.items.info

Get a row from a list |                                                                  Get a row from a list                                                                  |
| slackLists.items.list

Get records from a list |                                                                 Get records from a list                                                                 |
| slackLists.items.update

Updates cells in a list |                                                                 Updates cells in a list                                                                 |
| slackLists.update

Update a list |                                                                      Update a list                                                                      |
| stars.add

Save an item for later. Formerly known as adding a star. |                                                Save an item for later. Formerly known as adding a star.                                                 |
| stars.remove

Removes a saved item (star) from an item. |                                                        Removes a saved item (star) from an item.                                                        |
| team.info

Gets information about the current team. |                                                        Gets information about the current team.                                                         |
| usergroups.create

Create a User Group. |                                                                  Create a User Group.                                                                   |
| usergroups.disable

Disable an existing User Group. |                                                             Disable an existing User Group.                                                             |
| usergroups.enable

Enable a User Group. |                                                                  Enable a User Group.                                                                   |
| usergroups.update

Update an existing User Group. |                                                             Update an existing User Group.                                                              |
| usergroups.users.update

Update the list of users for a user group. |                                                       Update the list of users for a user group.                                                        |
| users.discoverableContacts.lookup

Look up an email address to see if someone is discoverable on Slack |                                           Look up an email address to see if someone is discoverable on Slack                                           |
| users.profile.set

Set a user's profile information, including custom status. |                                               Set a user's profile information, including custom status.                                                |
| users.setActive

Marked a user as active. Deprecated and non-functional. |                                                 Marked a user as active. Deprecated and non-functional.                                                 |
| users.setPresence

Manually sets user presence. |                                                              Manually sets user presence.                                                               |
| views.open

Open a view for a user. |                                                                 Open a view for a user.                                                                 |
| views.publish

Publish a static view for a User. |                                                            Publish a static view for a User.                                                            |
| views.push

Push a view onto the stack of a root view. |                                                       Push a view onto the stack of a root view.                                                        |
| views.update

Update an existing view. |                                                                Update an existing view.                                                                 |
| workflows.featured.add

Add featured workflows to a channel. |                                                          Add featured workflows to a channel.                                                           |
| workflows.featured.list

List the featured workflows for specified channels. |                                                   List the featured workflows for specified channels.                                                   |
| workflows.featured.remove

Remove featured workflows from a channel. |                                                        Remove featured workflows from a channel.                                                        |
| workflows.featured.set

Set featured workflows for a channel. |                                                          Set featured workflows for a channel.                                                          |
| workflows.stepCompleted

Indicate that an app's step in a workflow completed execution. |                                             Indicate that an app's step in a workflow completed execution.                                              |
| workflows.stepFailed

Indicate that an app's step in a workflow failed to execute. |                                              Indicate that an app's step in a workflow failed to execute.                                               |
| workflows.triggers.permissions.add

Allows users to run a trigger that has its permission type set to named\_entities |                                    Allows users to run a trigger that has its permission type set to named\_entities                                    |
| workflows.triggers.permissions.list

Returns the permission type of a trigger and if applicable, includes the entities that have been granted access |                     Returns the permission type of a trigger and if applicable, includes the entities that have been granted access                     |
| workflows.triggers.permissions.remove

Revoke an entity's access to a trigger that has its permission type set to named\_entities |                               Revoke an entity's access to a trigger that has its permission type set to named\_entities                                |
| workflows.triggers.permissions.set

Set the permission type for who can run a trigger |                                                    Set the permission type for who can run a trigger                                                    |
| workflows.updateStep

Update the configuration for a workflow step. |                                                      Update the configuration for a workflow step.                                                      |