[![](https://upload.wikimedia.org/wikipedia/labs/thumb/a/ad/EventStreams_Example.png/500px-EventStreams_Example.png)](https://codepen.io/ottomata/pen/LYpPpxj?editors=1010)[](https://wikitech.wikimedia.org/wiki/File:EventStreams_Example.png)

Example client at [codepen.io/ottomata/pen/LYpPpxj](https://codepen.io/ottomata/pen/LYpPpxj?editors=1010).

[![](https://upload.wikimedia.org/wikipedia/labs/thumb/f/f4/EventStreams_Example2.jpg/500px-EventStreams_Example2.jpg)](https://codepen.io/Krinkle/pen/BwEKgW?editors=1010)[](https://wikitech.wikimedia.org/wiki/File:EventStreams_Example2.jpg)

RecentChange stats tool, built with EventStreams – at [https://codepen.io/Krinkle/pen/BwEKgW](https://codepen.io/Krinkle/pen/BwEKgW?editors=1010).

**EventStreams** is a web service that exposes continuous streams of structured event data. It does so over HTTP using [chunked transfer encoding](https://en.wikipedia.org/wiki/Chunked_transfer_encoding) following the [Server-Sent Events](https://en.wikipedia.org/wiki/Server-sent_events "en:Server-sent events") protocol (SSE). EventStreams can be consumed directly via HTTP, but is more commonly used via a client library.

The service supersedes [RCStream](https://wikitech.wikimedia.org/wiki/Obsolete:RCStream "Obsolete:RCStream"), and might in the future replace [irc.wikimedia.org](https://wikitech.wikimedia.org/wiki/Irc.wikimedia.org "Irc.wikimedia.org"). EventStreams is internally backed by [Apache Kafka](https://kafka.apache.org/).

_Note: `SSE` and `EventSource` are often used interchangeably as the names of this web technology. This document refers to SSE as the server-side protocol, and EventSource as the client-side interface._

## Streams

EventStreams provides access to several different data streams, most notably the `recentchange` stream which emits [MediaWiki Recent changes](https://www.mediawiki.org/wiki/Manual:RCFeed "mw:Manual:RCFeed") events.

For a complete list of available streams, refer to the documentation at [https://stream.wikimedia.org/?doc#/streams](https://stream.wikimedia.org/?doc#/streams).

The data format of each stream follows a schema. The schemas can be obtained via [https://schema.wikimedia.org/#!/primary/jsonschema](https://schema.wikimedia.org/#!/primary/jsonschema), for example [jsonschema/mediawiki/recentchange/latest.yaml](https://schema.wikimedia.org/repositories/primary/jsonschema/mediawiki/recentchange/latest.yaml).

For the `recentchange` stream there is additional documentation at [Manual:RCFeed on mediawiki.org](https://www.mediawiki.org/wiki/Manual:RCFeed "mw:Manual:RCFeed").

### Wikidata RDF change stream

See [schema](https://schema.wikimedia.org/#!/primary/jsonschema/mediawiki/wikibase/entity/rdf_change) and [codepen where the stream can be selected and viewed in the browser](https://codepen.io/dpriskorn/pen/QwjgbNv?editors=1000) [example stream content](https://gist.github.com/dpriskorn/d8fdc0a03488f0382c3b1686862c1aed)

## When not to use EventStreams

The public EventStreams service is intended for use by small scale external tool developers. It should not be used to build production services within Wikimedia Foundation. WMF production services that react to events should directly consume the underlying Kafka topic(s).

## Examples

### Web browser

Use the built-in [EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) in modern browsers:

```
<span></span><span>const</span><span> </span><span>url</span><span> </span><span>=</span><span> </span><span>'https://stream.wikimedia.org/v2/stream/recentchange'</span><span>;</span>
<span>const</span><span> </span><span>eventSource</span><span> </span><span>=</span><span> </span><span>new</span><span> </span><span>EventSource</span><span>(</span><span>url</span><span>);</span>

<span>eventSource</span><span>.</span><span>onopen</span><span> </span><span>=</span><span> </span><span>()</span><span> </span><span>=&gt;</span><span> </span><span>{</span>
<span>    </span><span>console</span><span>.</span><span>info</span><span>(</span><span>'Opened connection.'</span><span>);</span>
<span>};</span>
<span>eventSource</span><span>.</span><span>onerror</span><span> </span><span>=</span><span> </span><span>(</span><span>event</span><span>)</span><span> </span><span>=&gt;</span><span> </span><span>{</span>
<span>    </span><span>console</span><span>.</span><span>error</span><span>(</span><span>'Encountered error'</span><span>,</span><span> </span><span>event</span><span>);</span>
<span>};</span>
<span>eventSource</span><span>.</span><span>onmessage</span><span> </span><span>=</span><span> </span><span>(</span><span>event</span><span>)</span><span> </span><span>=&gt;</span><span> </span><span>{</span>
<span>    </span><span>// event.data will be a JSON message</span>
<span>    </span><span>const</span><span> </span><span>data</span><span> </span><span>=</span><span> </span><span>JSON</span><span>.</span><span>parse</span><span>(</span><span>event</span><span>.</span><span>data</span><span>);</span>
<span>    </span><span>// discard all canary events</span>
<span>    </span><span>if</span><span> </span><span>(</span><span>data</span><span>.</span><span>meta</span><span>.</span><span>domain</span><span> </span><span>===</span><span> </span><span>'canary'</span><span>)</span><span> </span><span>{</span>
<span>        </span><span>return</span><span>;</span>
<span>    </span><span>}</span>
<span>    </span><span>// Edits from English Wikipedia</span>
<span>    </span><span>if</span><span> </span><span>(</span><span>data</span><span>.</span><span>server_name</span><span> </span><span>===</span><span> </span><span>'en.wikipedia.org'</span><span>)</span><span> </span><span>{</span>
<span>        </span><span>// Output the title of the edited page</span>
<span>        </span><span>console</span><span>.</span><span>log</span><span>(</span><span>data</span><span>.</span><span>title</span><span>);</span>
<span>    </span><span>}</span>
<span>};</span>
```

### JavaScript

#### Node.js ESM (with [wikimedia-streams](https://www.npmjs.com/package/wikimedia-streams))

```
<span></span><span>import</span><span> </span><span>WikimediaStream</span><span> </span><span>from</span><span> </span><span>'wikimedia-streams'</span><span>;</span>

<span>// 'recentchange' can be replaced with another stream topic</span>
<span>const</span><span> </span><span>stream</span><span> </span><span>=</span><span> </span><span>new</span><span> </span><span>WikimediaStream</span><span>(</span><span>'recentchange'</span><span>);</span>

<span>stream</span><span>.</span><span>on</span><span>(</span><span>'open'</span><span>,</span><span> </span><span>()</span><span> </span><span>=&gt;</span><span> </span><span>{</span>
<span>    </span><span>console</span><span>.</span><span>info</span><span>(</span><span>'Opened connection.'</span><span>);</span>
<span>});</span>
<span>stream</span><span>.</span><span>on</span><span>(</span><span>'error'</span><span>,</span><span> </span><span>(</span><span>event</span><span>)</span><span> </span><span>=&gt;</span><span> </span><span>{</span>
<span>    </span><span>console</span><span>.</span><span>error</span><span>(</span><span>'Encountered error'</span><span>,</span><span> </span><span>event</span><span>);</span>
<span>});</span>
<span>stream</span>
<span>    </span><span>.</span><span>filter</span><span>(</span><span>"mediawiki.recentchange"</span><span>)</span>
<span>    </span><span>.</span><span>all</span><span>({</span><span> </span><span>wiki</span><span>:</span><span> </span><span>"enwiki"</span><span> </span><span>})</span><span> </span><span>// Edits from English Wikipedia</span>
<span>    </span><span>.</span><span>on</span><span>(</span><span>'recentchange'</span><span>,</span><span> </span><span>(</span><span>data</span><span>,</span><span> </span><span>event</span><span>)</span><span> </span><span>=&gt;</span><span> </span><span>{</span>
<span>        </span><span>// Output page title</span>
<span>        </span><span>console</span><span>.</span><span>log</span><span>(</span><span>data</span><span>.</span><span>title</span><span>);</span>
<span>    </span><span>});</span>
```

#### Node.js (with [eventsource](https://github.com/aslakhellesoy/eventsource))

```
<span></span><span>import</span><span> </span><span>{</span><span>EventSource</span><span>}</span><span> </span><span>from</span><span> </span><span>'eventsource'</span><span>;</span>

<span>const</span><span> </span><span>url</span><span> </span><span>=</span><span> </span><span>'https://stream.wikimedia.org/v2/stream/recentchange'</span><span>;</span>
<span>const</span><span> </span><span>eventSource</span><span> </span><span>=</span><span> </span><span>new</span><span> </span><span>EventSource</span><span>(</span><span>url</span><span>);</span>

<span>eventSource</span><span>.</span><span>onopen</span><span> </span><span>=</span><span> </span><span>()</span><span> </span><span>=&gt;</span><span> </span><span>{</span>
<span>    </span><span>console</span><span>.</span><span>info</span><span>(</span><span>'Opened connection.'</span><span>);</span>
<span>};</span>
<span>eventSource</span><span>.</span><span>onerror</span><span> </span><span>=</span><span> </span><span>(</span><span>event</span><span>)</span><span> </span><span>=&gt;</span><span> </span><span>{</span>
<span>    </span><span>console</span><span>.</span><span>error</span><span>(</span><span>'Encountered error'</span><span>,</span><span> </span><span>event</span><span>);</span>
<span>};</span>
<span>eventSource</span><span>.</span><span>onmessage</span><span> </span><span>=</span><span> </span><span>(</span><span>event</span><span>)</span><span> </span><span>=&gt;</span><span> </span><span>{</span>
<span>    </span><span>const</span><span> </span><span>data</span><span> </span><span>=</span><span> </span><span>JSON</span><span>.</span><span>parse</span><span>(</span><span>event</span><span>.</span><span>data</span><span>);</span>
<span>    </span><span>// discard canary events</span>
<span>    </span><span>if</span><span> </span><span>(</span><span>data</span><span>.</span><span>meta</span><span>.</span><span>domain</span><span> </span><span>===</span><span> </span><span>'canary'</span><span>)</span><span> </span><span>{</span>
<span>        </span><span>return</span><span>;</span>
<span>    </span><span>}</span>
<span>    </span><span>if</span><span> </span><span>(</span><span>data</span><span>.</span><span>server_name</span><span> </span><span>===</span><span> </span><span>'en.wikipedia.org'</span><span>)</span><span> </span><span>{</span>
<span>        </span><span>// Output the page title</span>
<span>        </span><span>console</span><span>.</span><span>log</span><span>(</span><span>data</span><span>.</span><span>title</span><span>);</span>
<span>    </span><span>}</span>
<span>};</span>
```

Server side filtering is not supported. You can filter client-side instead, for example to listen for changes to a specific wiki only:

```
<span></span><span>var</span><span> </span><span>wiki</span><span> </span><span>=</span><span> </span><span>'commonswiki'</span><span>;</span>
<span>eventSource</span><span>.</span><span>onmessage</span><span> </span><span>=</span><span> </span><span>function</span><span>(</span><span>event</span><span>)</span><span> </span><span>{</span>
<span>    </span><span>// event.data will be a JSON string containing the message event.</span>
<span>    </span><span>var</span><span> </span><span>change</span><span> </span><span>=</span><span> </span><span>JSON</span><span>.</span><span>parse</span><span>(</span><span>event</span><span>.</span><span>data</span><span>);</span>
<span>    </span><span>// discard canary events</span>
<span>    </span><span>if</span><span> </span><span>(</span><span>change</span><span>.</span><span>meta</span><span>.</span><span>domain</span><span> </span><span>===</span><span> </span><span>'canary'</span><span>)</span><span> </span><span>{</span>
<span>        </span><span>return</span><span>;</span>
<span>    </span><span>}</span><span>    </span>
<span>    </span><span>if</span><span> </span><span>(</span><span>change</span><span>.</span><span>wiki</span><span> </span><span>==</span><span> </span><span>wiki</span><span>)</span>
<span>        </span><span>console</span><span>.</span><span>log</span><span>(</span><span>`Got commons wiki change on page </span><span>${</span><span>change</span><span>.</span><span>title</span><span>}</span><span>`</span><span>);</span>
<span>};</span>
```

### TypeScript

#### Node.js (with [wikimedia-streams](https://www.npmjs.com/package/wikimedia-streams))

```
<span></span><span>import</span><span> </span><span>WikimediaStream</span><span> </span><span>from</span><span> </span><span>"wikimedia-streams"</span><span>;</span>
<span>import</span><span> </span><span>MediaWikiRecentChangeEvent</span><span> </span><span>from</span><span> </span><span>'wikimedia-streams/build/streams/MediaWikiRecentChangeEvent'</span><span>;</span>

<span>// "recentchange" can be replaced with any valid stream</span>
<span>const</span><span> </span><span>stream</span><span> </span><span>=</span><span> </span><span>new</span><span> </span><span>WikimediaStream</span><span>(</span><span>"recentchange"</span><span>);</span>

<span>stream</span>
<span>    </span><span>.</span><span>filter</span><span>(</span><span>"mediawiki.recentchange"</span><span>)</span>
<span>    </span><span>.</span><span>all</span><span>({</span><span> </span><span>wiki</span><span>:</span><span> </span><span>"enwiki"</span><span> </span><span>})</span><span> </span><span>// Edits from English Wikipedia</span>
<span>    </span><span>.</span><span>on</span><span>(</span><span>'recentchange'</span><span>,</span><span> </span><span>(</span><span>data</span><span> </span><span>/* MediaWikiRecentChangeEvent &amp; { wiki: 'enwiki' } */</span><span>,</span><span> </span><span>event</span><span>)</span><span> </span><span>=&gt;</span><span> </span><span>{</span>
<span>        </span><span>// Output page title</span>
<span>        </span><span>console</span><span>.</span><span>log</span><span>(</span><span>data</span><span>.</span><span>title</span><span>);</span>
<span>    </span><span>});</span>
```

### Python

Using [requests-sse](https://pypi.org/project/requests-sse/). Other clients can be found at [T309380 #10304093](https://phabricator.wikimedia.org/T309380#10304093 "phab:T309380").

```
<span></span><span>import</span><span> </span><span>json</span>
<span>from</span><span> </span><span>requests_sse</span><span> </span><span>import</span> <span>EventSource</span>

<span>url</span> <span>=</span> <span>'https://stream.wikimedia.org/v2/stream/recentchange'</span>
<span>with</span> <span>EventSource</span><span>(</span><span>url</span><span>)</span> <span>as</span> <span>stream</span><span>:</span>
    <span>for</span> <span>event</span> <span>in</span> <span>stream</span><span>:</span>
        <span>if</span> <span>event</span><span>.</span><span>type</span> <span>==</span> <span>'message'</span><span>:</span>
            <span>try</span><span>:</span>
                <span>change</span> <span>=</span> <span>json</span><span>.</span><span>loads</span><span>(</span><span>event</span><span>.</span><span>data</span><span>)</span>
            <span>except</span> <span>ValueError</span><span>:</span>
                <span>pass</span>
            <span>else</span><span>:</span>
                <span># discard canary events</span>
                <span>if</span> <span>change</span><span>[</span><span>'meta'</span><span>][</span><span>'domain'</span><span>]</span> <span>==</span> <span>'canary'</span><span>:</span>
                    <span>continue</span>            
                <span>print</span><span>(</span><span>'</span><span>{user}</span><span> edited </span><span>{title}</span><span>'</span><span>.</span><span>format</span><span>(</span><span>**</span><span>change</span><span>))</span>
```

The standard SSE protocol defines ways to continue where you left after a failure or other disconnect. We support this in EventStreams as well. For example:

```
<span></span><span>import</span><span> </span><span>json</span>
<span>from</span><span> </span><span>requests_sse</span><span> </span><span>import</span> <span>EventSource</span>

<span>url</span> <span>=</span> <span>'https://stream.wikimedia.org/v2/stream/recentchange'</span>
<span>last_id</span> <span>=</span> <span>None</span>
<span>with</span> <span>EventSource</span><span>(</span><span>url</span><span>)</span> <span>as</span> <span>stream</span><span>:</span>
    <span>for</span> <span>event</span> <span>in</span> <span>stream</span><span>:</span>
        <span>if</span> <span>event</span><span>.</span><span>type</span> <span>==</span> <span>'message'</span><span>:</span>
            <span>try</span><span>:</span>
                <span>change</span> <span>=</span> <span>json</span><span>.</span><span>loads</span><span>(</span><span>event</span><span>.</span><span>data</span><span>)</span>
            <span>except</span> <span>ValueError</span><span>:</span>
                <span>pass</span>
            <span>else</span><span>:</span>
                <span># discard canary events</span>
                <span>if</span> <span>change</span><span>[</span><span>'meta'</span><span>][</span><span>'domain'</span><span>]</span> <span>==</span> <span>'canary'</span><span>:</span>
                    <span>continue</span>            
                <span>if</span> <span>change</span><span>.</span><span>user</span> <span>==</span> <span>'Yourname'</span><span>:</span>
                    <span>print</span><span>(</span><span>change</span><span>)</span>
                    <span>last_id</span> <span>=</span> <span>event</span><span>.</span><span>last_event_id</span>
                    <span>print</span><span>(</span><span>last_id</span><span>)</span>            

<span># - Run this Python script.</span>
<span># - Publish an edit to <a href="https://wikitech.wikimedia.org/wiki/Sandbox" title="Sandbox">[[Sandbox]]</a> on test.wikipedia.org, and observe it getting printed.</span>
<span># - Quit the Python process.</span>
<span># - Pass last_id to last_event_id parameter when creating the stream like</span>
<span>#   with EventSource(url,  latest_event_id=last_id) as stream: ...</span>
<span># - Publish another edit, while the Python process remains off.</span>
<span># - Run this Python script again, and notice it finding and printing the missed edit.</span>
```

Server-side filtering is not supported. To filter for something like a wiki domain, you'll need to do this on the consumer side side. For example:

```
<span></span><span>wiki</span> <span>=</span> <span>'commonswiki'</span>
<span>with</span> <span>EventSource</span><span>(</span><span>url</span><span>)</span> <span>as</span> <span>stream</span><span>:</span>
    <span>for</span> <span>event</span> <span>in</span> <span>stream</span><span>:</span>
        <span>if</span> <span>event</span><span>.</span><span>type</span> <span>==</span> <span>'message'</span><span>:</span>
            <span>try</span><span>:</span>
                <span>change</span> <span>=</span> <span>json</span><span>.</span><span>loads</span><span>(</span><span>event</span><span>.</span><span>data</span><span>)</span>
            <span>except</span> <span>ValueError</span><span>:</span>
                <span>pass</span>
            <span>else</span><span>:</span>
                <span># discard canary events</span>
                <span>if</span> <span>change</span><span>[</span><span>'meta'</span><span>][</span><span>'domain'</span><span>]</span> <span>==</span> <span>'canary'</span><span>:</span>
                    <span>continue</span>            
            <span>if</span> <span>change</span><span>[</span><span>'wiki'</span><span>]</span> <span>==</span> <span>wiki</span><span>:</span>
                <span>print</span><span>(</span><span>'</span><span>{user}</span><span> edited </span><span>{title}</span><span>'</span><span>.</span><span>format</span><span>(</span><span>**</span><span>change</span><span>))</span>
```

[Pywikibot](https://www.mediawiki.org/wiki/Manual:Pywikibot "mw:Manual:Pywikibot") is another way to consume EventStreams in Python. It provides an abstraction that takes care of automatic reconnection, easy filtering, and combination of multiple topics into one stream. For example:

```
<span></span><span>&gt;&gt;&gt;</span> <span>from</span><span> </span><span>pywikibot.comms.eventstreams</span><span> </span><span>import</span> <span>EventStreams</span>
<span>&gt;&gt;&gt;</span> <span>stream</span> <span>=</span> <span>EventStreams</span><span>(</span><span>streams</span><span>=</span><span>[</span><span>'recentchange'</span><span>,</span> <span>'revision-create'</span><span>],</span> <span>since</span><span>=</span><span>'20250107'</span><span>)</span>
<span>&gt;&gt;&gt;</span> <span>stream</span><span>.</span><span>register_filter</span><span>(</span><span>server_name</span><span>=</span><span>'fr.wikipedia.org'</span><span>,</span> <span>type</span><span>=</span><span>'edit'</span><span>)</span>
<span>&gt;&gt;&gt;</span> <span>change</span> <span>=</span> <span>next</span><span>(</span><span>stream</span><span>)</span>
<span>&gt;&gt;&gt;</span> <span>print</span><span>(</span><span>'</span><span>{type}</span><span> on page "</span><span>{title}</span><span>" by "</span><span>{user}</span><span>" at </span><span>{meta[dt]}</span><span>.'</span><span>.</span><span>format</span><span>(</span><span>**</span><span>change</span><span>))</span>
<span>edit</span> <span>on</span> <span>page</span> <span>"Véronique Le Guen"</span> <span>by</span> <span>"Speculos"</span> <span>at</span> <span>2019</span><span>-</span><span>01</span><span>-</span><span>12</span><span>T21</span><span>:</span><span>19</span><span>:</span><span>43</span><span>+</span><span>00</span><span>:</span><span>00.</span>
```

### Command-line

With [curl](https://linux.die.net/man/1/curl) and [jq](https://stedolan.github.io/jq/manual/) Set the Accept header and prettify the events with jq.

```
<span></span>curl<span> </span>-s<span> </span>-H<span> </span><span>'Accept: application/json'</span><span>  </span>https://stream.wikimedia.org/v2/stream/recentchange<span> </span><span>|</span><span> </span>jq<span> </span>.
```

Setting the Accept: application/json will cause EventStreams to send you newline delimited JSON objects, rather than data in the SSE format.

## API

The list of streams that are available will change over time, so they will not be documented here. To see the active list of available streams, visit the [swagger-ui documentation](https://stream.wikimedia.org/?doc), or request the swagger spec directly from [https://stream.wikimedia.org/?spec](https://stream.wikimedia.org/?spec). The available stream URI paths all begin with `/v2/stream`, e.g.

```
<span></span><span>"/v2/stream/recentchange"</span><span>:</span><span> </span><span>{</span>
<span>    </span><span>"get"</span><span>:</span><span> </span><span>{</span>
<span>      </span><span>"produces"</span><span>:</span><span> </span><span>[</span>
<span>        </span><span>"text/event-stream; charset=utf-8"</span>
<span>      </span><span>],</span>
<span>      </span><span>"description"</span><span>:</span><span> </span><span>"Mediawiki RecentChanges feed. Schema: https://schema.wikimedia.org/#!//primary/jsonschema/mediawiki/recentchange"</span>
<span>    </span><span>}</span>
<span>  </span><span>},</span>
<span>"/v2/stream/revision-create"</span><span>:</span><span> </span><span>{</span>
<span>      </span><span>"get"</span><span>:</span><span> </span><span>{</span>
<span>        </span><span>"produces"</span><span>:</span><span> </span><span>[</span>
<span>          </span><span>"text/event-stream; charset=utf-8"</span>
<span>        </span><span>],</span>
<span>        </span><span>"description"</span><span>:</span><span> </span><span>"Mediawiki Revision Create feed. Schema: https://schema.wikimedia.org/#!//primary/jsonschema/mediawiki/revision/create"</span>
<span>      </span><span>}</span>
<span>    </span><span>}</span>
```

### Stream selection

Streams are addressable either individually, e.g. `/v2/stream/revision-create`, or as a comma separated list of streams to compose, e.g. `/v2/stream/page-create,page-delete,page-undelete`.

See available streams: [https://stream.wikimedia.org/?doc](https://stream.wikimedia.org/?doc)

### Historical Consumption

Since 2018-06, EventStreams supports timestamp based historical consumption. This can be provided as individual assignment objects in the `Last-Event-ID` by setting a timestamp field instead of an offset field. Or, more simply, a `since` query parameter can be provided in the stream URL, e.g. `since=2018-06-14T00:00:00Z`. `since` can either be given as anything parseable by Javascript `Date.parse()`, e.g. a UTC [ISO-8601](https://en.m.wikipedia.org/wiki/ISO_8601) datetime string.

When given a timestamp, EventStreams will ask Kafka for the message offset in the stream(s) that most closely match the timestamp. Kafka guarantees that all events after the returned message offset will be after the given timestamp. NOTE: The stream history is not kept indefinitely. Depending on the stream configuration, there will likely be between 7 and 31 days of history available. Please be kind when providing timestamps. There may be a lot of historical data available, and reading it and sending it all out can be compute resource intensive. Please only consume the minimum of data you need.

Example URL: [https://stream.wikimedia.org/v2/stream/revision-create?since=2016-06-14T00:00:00Z](https://stream.wikimedia.org/v2/stream/revision-create?since=2016-06-14T00:00:00Z).

If you want to manually set which topics, partitions, and timestamps or offsets your client starts consuming from, you can set the Last-Event-ID HTTP request header to an array of objects that specify this. E.g.

`[{"topic": "eqiad.mediawiki.recentchange", "partition": 0, "offset": 1234567}, {"topic": "codfw.mediawiki.recentchange", "partition": 0, "timestamp": 1575906290000}]`

### Response Format

All examples here will consume recent changes from [https://stream.wikimedia.org/v2/stream/recentchange](https://stream.wikimedia.org/v2/stream/recentchange). This section describes the format of a response body from a EventStreams stream endpoint.

Requesting `/v2/stream/recentchange` will start a stream of data in the SSE format. This format is best interpreted using an EventSource client. If you choose not to use one of these, the raw stream is still human readable and looks as follows:

```
<span></span><span>eve</span><span>nt</span><span>:</span><span> </span><span>message</span>
<span>id</span><span>:</span><span> </span><span>[{</span><span>"topic"</span><span>:</span><span>"eqiad.mediawiki.recentchange"</span><span>,</span><span>"partition"</span><span>:</span><span>0</span><span>,</span><span>"timestamp"</span><span>:</span><span>1532031066001</span><span>},{</span><span>"topic"</span><span>:</span><span>"codfw.mediawiki.recentchange"</span><span>,</span><span>"partition"</span><span>:</span><span>0</span><span>,</span><span>"offset"</span><span>:</span><span>-1</span><span>}]</span>
<span>da</span><span>ta</span><span>:</span><span> </span><span>{</span><span>"event"</span><span>:</span><span> </span><span>"data"</span><span>,</span><span> </span><span>"is"</span><span>:</span><span> </span><span>"here"</span><span>}</span>
```

Each event will be separated by 2 line breaks (`\n\n`), and have `event`, `id`, and `data` fields.

The `event` will be `message` for data events, and `error` for error events. `id` is a JSON-formatted array of Kafka topic, partition and offset|timestamp metadata. The `id` field can be used to tell EventStreams to start consuming from an earlier position in the stream. This enables clients to automatically resume from where they left off if they are disconnected. EventSource implementations handle this transparently. Note that the topic partition and offset|timestamp for all topics and partitions that make up this stream are included in every message's id field. This allows EventSource to be specific about where it left off even if the consumed stream is composed of multiple Kafka topic-partitions.

Note that offsets and timestamps may be used interchangeably SSE `id`. WMF runs stream.wikimedia.org in a multi-DC active/active setup, backed by multiple Kafka clusters. Since Kafka offsets are unique per cluster, using them in a multi DC setup is not reliable. Instead, `id` fields will always use timestamps instead of offsets. This is not as precise as using offsets, but allows for a reliable multi DC service.

You may request that EventStreams begins streaming to you from different offsets by setting an array of topic, partition, offset|timestamp objects in the Last-Event-ID HTTP header.

### Canary Events

WMF [Data Engineering team](https://wikitech.wikimedia.org/wiki/Data_Engineering "Data Engineering") [produces artificial 'canary' events](https://wikitech.wikimedia.org/wiki/Data_Engineering/Systems/Hadoop_Event_Ingestion_Lifecycle "Data Engineering/Systems/Hadoop Event Ingestion Lifecycle") into each stream multiple times an hour. The presence of these canary events in a stream allow us to differentiate between a broken event stream, and an empty one. If a stream has canary\_events\_enabled=true, then we should expect at least one event in a stream's Kafka topics every hour. If we get no events in an hour, then we can trigger an alert that a stream is broken.

These events are not filtered out in the streams available at [stream.wikimedia.org](https://wikitech.wikimedia.org/wiki/Stream.wikimedia.org "Stream.wikimedia.org"). As a user of these streams, you should discard all canary events; i.e. all events where `meta.domain === 'canary'`.

**If you are not using canary events for alerting, discard them!** Discard all events where

```
meta.domain === 'canary'
```

The content of most canary event fields are copied directly from the first example event in the event's schema. E.g. [mediawiki/recentchange example](https://github.com/wikimedia/schemas-event-primary/blob/master/jsonschema/mediawiki/recentchange/1.0.1.yaml#L159), [mediawiki/revision/create example](https://github.com/wikimedia/schemas-event-primary/blob/master/jsonschema/mediawiki/revision/create/2.0.0.yaml#L288). These examples can also be seen in the [OpenAPI docs for the streams](https://stream.wikimedia.org/?doc#/streams), e.g. [mediawiki.page-move example value](https://stream.wikimedia.org/?doc#/streams/get_v2_stream_mediawiki_page_move). The code that creates canary events can be found [here](https://gerrit.wikimedia.org/r/plugins/gitiles/wikimedia-event-utilities/%2B/refs/heads/master/eventutilities/src/main/java/org/wikimedia/eventutilities/monitoring/CanaryEventProducer.java#118 "gerrit:plugins/gitiles/wikimedia-event-utilities/+/refs/heads/master/eventutilities/src/main/java/org/wikimedia/eventutilities/monitoring/CanaryEventProducer.java") (as of 2023-11).

### Filtering

EventStreams does not have $wgServerName (or any other) server side filtering capabilities. You'll need to do your filtering client side, e.g.

```
<span></span><span>/**</span>
<span> * Calls cb(event) for every event where recentchange event.server_name == server_name.</span>
<span> */</span>
<span>function</span><span> </span><span>filterWiki</span><span>(</span><span>event</span><span>,</span><span> </span><span>server_name</span><span>,</span><span> </span><span>cb</span><span>)</span><span> </span><span>{</span>
<span>    </span><span>if</span><span> </span><span>(</span><span>event</span><span>.</span><span>server_name</span><span> </span><span>==</span><span> </span><span>server_name</span><span>)</span><span> </span><span>{</span>
<span>        </span><span>cb</span><span>(</span><span>event</span><span>);</span>
<span>    </span><span>}</span>
<span>}</span>

<span>eventSource</span><span>.</span><span>onmessage</span><span> </span><span>=</span><span> </span><span>function</span><span>(</span><span>event</span><span>)</span><span> </span><span>{</span>
<span>    </span><span>// Print only events that come from Wikimedia Commons.</span>
<span>    </span><span>filterWiki</span><span>(</span><span>JSON</span><span>.</span><span>parse</span><span>(</span><span>event</span><span>.</span><span>data</span><span>),</span><span> </span><span>'commons.wikimedia.org'</span><span>,</span><span> </span><span>console</span><span>.</span><span>log</span><span>);</span>
<span>};</span>
```

## Architecture

### SSE vs. WebSockets/Socket.IO

The previous "RCStream" service was written for consumption via Socket.IO, so why did we change the protocol for its replacement?

The WebSocket protocol doesn't use HTTP, which makes it different from most other services we run at Wikimedia Foundation. WebSockets are powerful and can e.g. let clients and servers communicate asynchronously with a bi-directional pipe. EventStreams, on the other hand, is read-only and only needs to send events from the server to a client. By using only 100% standard HTTP, EventStreams can be consumed from any HTTP client out there, without the need for programming several RPC-like initialization steps.

We originally prototyped a Kafka -> Socket.io library ([Kasocki](https://github.com/wikimedia/kasocki)). After doing so we decided that HTTP-SSE was a better fit, and developed [KafkaSSE](https://github.com/wikimedia/kafkasse) instead.

### KafkaSSE

KafkaSSE is a library that glues a Kafka Consumer to a connected HTTP SSE client. A Kafka Consumer is assigned topics, partitions, and offsets, and then events are streamed from the consumer to the HTTP client in [chunked-transfer encoding](https://en.wikipedia.org/wiki/Chunked_transfer_encoding). EventStreams maps stream routes (e.g /v2/stream/recentchanges) to specific topics in Kafka.

### Kafka

WMF maintains several internal [Kafka](https://wikitech.wikimedia.org/wiki/Kafka "Kafka") clusters, producing hundreds of thousands of messages per second. It has proved to be highly scalable and feature-ful. It is multi producer and multi consumer. Our internal events are already produced through Kafka, so using it as the EventStreams backend was a natural choice.

Kafka allows us to begin consuming from any message offset (that is still present on the backend Kafka cluster). This feature is what allows connected EventStreams clients to auto-resume (via EventSource) when they disconnect.

## Notes

### Server side enforced timeout

WMF's HTTP connection termination layer enforces a connection timeout of 15 minutes. A good SSE / EventSource client should be able to automatically reconnect and begin consuming at the right location using the Last-Event-ID header.

See [this Phabricator discussion](https://phabricator.wikimedia.org/T242767#6202636) for more info.

## See also

-   [EventStreams/Administration](https://wikitech.wikimedia.org/wiki/EventStreams/Administration "EventStreams/Administration"), for WMF administration.

-   [EventStreams/Powered By](https://wikitech.wikimedia.org/wiki/EventStreams/Powered_By "EventStreams/Powered By"), for a list of example tools that are built on EventStreams.
-   [Event\*](https://wikitech.wikimedia.org/wiki/Event* "Event*"), disambiguation for various event-related services at Wikimedia.
-   [RCStream](https://wikitech.wikimedia.org/wiki/Obsolete:RCStream "Obsolete:RCStream"), predecessor to EventStreams.
-   [Manual:RCFeed](https://www.mediawiki.org/wiki/Manual:RCFeed "mw:Manual:RCFeed") on mediawiki.org, about the underlying format of the recent changes messages.
-   [Manual:$wgRCFeeds](https://www.mediawiki.org/wiki/Manual:$wgRCFeeds "mw:Manual:$wgRCFeeds") on mediawiki.org, about setting up RCFeed (EventStreams uses the EventBusRCEngine from [EventBus](https://www.mediawiki.org/wiki/Extension:EventBus "mw:Extension:EventBus")).
-   [API:Recent changes stream](https://www.mediawiki.org/wiki/API:Recent_changes_stream "mw:API:Recent changes stream") on mediawiki.org.

## Further reading

-   ["Get live updates to Wikimedia projects with EventStreams"](https://diff.wikimedia.org/2017/03/20/eventstreams/ "wmfblog:2017/03/20/eventstreams/"), by Andrew Otto (2017).
-   ["EventStreams updates: New events, composite streams, historical subscription"](https://diff.wikimedia.org/2018/08/08/eventstreams-updates/ "wmfblog:2018/08/08/eventstreams-updates/"), by Andrew Otto (2018).

-   ["Server-Sent Events: the alternative to WebSockets you should be using"](https://germano.dev/sse-websockets/), by Germano Gabbianelli (2022).

## External links

-   [Source code of eventstreams service](https://gitlab.wikimedia.org/repos/data-engineering/eventstreams "gitlab:repos/data-engineering/eventstreams") ([GitHub mirror](https://github.com/wikimedia/mediawiki-services-eventstreams))
-   [Source code node-kafka-sse library](https://github.com/wikimedia/KafkaSSE)
-   [Issue tracker (Phabricator workboard)](https://phabricator.wikimedia.org/tag/wikimedia-stream "phab:tag/wikimedia-stream")
-   [How to track the main Wikidata RDF stream using QLever to have a local up-to-date instance](https://github.com/ad-freiburg/qlever/discussions/2276).