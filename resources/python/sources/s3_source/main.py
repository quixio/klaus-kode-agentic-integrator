from quixstreams import Application
from quixstreams.sources.community.file import FileSource
from quixstreams.sources.community.file.origins import S3Origin

import os
from dotenv import load_dotenv
load_dotenv()

app = Application()

# create an output topic
output_topic = app.topic(os.environ['output'])

# describe the file origin and access credentials
origin = S3Origin(
    bucket=os.environ['S3_BUCKET'],
    aws_access_key_id=os.environ['S3_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['S3_SECRET'],
    region_name=os.environ['S3_REGION'],
)

# create a file source, describing the file path and formats
source = FileSource(
    directory=os.environ['S3_FOLDER_PATH'],
    origin=origin,
    format=os.environ['S3_FILE_FORMAT'],
    compression=os.environ['S3_FILE_COMPRESSION'],
)

app.add_source(source)

if __name__ == "__main__":
    app.run()