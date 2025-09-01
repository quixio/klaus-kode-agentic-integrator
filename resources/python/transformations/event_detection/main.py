import os
from quixstreams import Application
from datetime import datetime

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

app = Application(consumer_group="hard-braking-v1", auto_offset_reset="earliest", use_changelog_topics=False)

input_topic = app.topic(os.environ["input"])
output_topic = app.topic(os.environ["output"])

sdf = app.dataframe(input_topic)

# Filter items out without brake value.
sdf = sdf[sdf.contains("Brake")]

# Calculate hopping window of 1s with 200ms steps.
sdf = sdf.apply(lambda row: float(row["Brake"])) \
        .hopping_window(1000, 200).mean().final() 
        
sdf.print()

# Filter only windows where average brake force exceeded 50%.
sdf = sdf[sdf["value"] > 0.5]

# Create nice JSON alert message.
sdf = sdf.apply(lambda row: {
    "Timestamp": str(datetime.fromtimestamp(row["start"]/1000)),
    "Alert": {
        "Title": "Hard braking detected.",
        "Message": "For last 1 second, average braking power was " + str(row["value"])
    }
})

# Print JSON messages in console.
sdf.print()

# Send the message to the output topic
sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run()