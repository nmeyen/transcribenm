import streamlit as st
import boto3
import uuid
import time
import os
import requests

# AWS configuration – replace with your actual bucket names and region.
AWS_REGION = 'ap-south-1'
INPUT_BUCKET = 'awstranscribeinput'    # Pre-created S3 bucket for audio files
OUTPUT_BUCKET = 'awstranscribeoutput'  # Pre-created S3 bucket for transcription results


## Initialize AWS clients
s3_client = boto3.client(
    's3',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)
transcribe_client = boto3.client(
    'transcribe',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)


def upload_to_s3(file_obj, bucket, object_name):
    """
    Uploads the provided file object to the specified S3 bucket.
    Returns the S3 URI of the uploaded file.
    """
    s3_client.upload_fileobj(file_obj, bucket, object_name)
    s3_uri = f"s3://{bucket}/{object_name}"
    return s3_uri

def start_transcription(s3_uri, job_name, language_code="en-US", media_format="mp3"):
    """
    Initiates an AWS Transcribe job for the file at the given S3 URI.
    The transcription output is directed to the OUTPUT_BUCKET.
    """
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': s3_uri},
        MediaFormat=media_format,
        LanguageCode=language_code,
        OutputBucketName=OUTPUT_BUCKET  # Ensure this bucket is set with proper permissions.
    )

def get_transcription_result(job_name):
    """
    Polls AWS Transcribe until the job completes. Once complete,
    fetches and returns the transcript text.
    """
    while True:
        status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        job_status = status['TranscriptionJob']['TranscriptionJobStatus']
        if job_status in ['COMPLETED', 'FAILED']:
            break
        st.write("Transcription in progress... Please wait.")
        time.sleep(5)  # Poll every 5 seconds

    if job_status == 'COMPLETED':
        transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        response = requests.get(transcript_uri)
        transcript_data = response.json()
        transcript = transcript_data['results']['transcripts'][0]['transcript']
        return transcript
    else:
        return "Transcription failed. Please check AWS Transcribe logs for details."

def main():
    st.title("AWS Transcribe Demo App")
    st.markdown("Upload an audio file to see AWS Transcribe in action.")

    # Allow the user to upload an audio file.
    audio_file = st.file_uploader("Choose an audio file", type=["mp3", "wav", "mp4"])
    
    if audio_file is not None:
        # Determine media format from the file extension.
        _, ext = os.path.splitext(audio_file.name)
        media_format = ext[1:].lower() if ext else "mp3"
        
        st.audio(audio_file, format=f"audio/{media_format}")
        
        if st.button("Transcribe Audio"):
            # Create unique identifiers for the S3 object and transcription job.
            file_key = f"audio-{uuid.uuid4()}{ext}"
            job_name = f"transcription-job-{uuid.uuid4()}"
            
            # Upload the audio file to S3.
            s3_uri = upload_to_s3(audio_file, INPUT_BUCKET, file_key)
            st.write("File uploaded to S3:", s3_uri)
            
            # Start the transcription job.
            start_transcription(s3_uri, job_name, media_format=media_format)
            st.write("Transcription job started. Job name:", job_name)
            
            # Retrieve and display the transcription result.
            transcript = get_transcription_result(job_name)
            st.markdown("### Transcription Result:")
            st.write(transcript)

if __name__ == "__main__":
    main()
