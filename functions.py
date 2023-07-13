import glob

import boto3
import configparser
import os
from pathlib import Path
from bs4 import BeautifulSoup

endpoint_url = 'https://storage.yandexcloud.net'


def init(access_key_id, secret_access_key, bucket_name):
    config = configparser.ConfigParser()

    user_config_dir = os.path.expanduser("~") + r'/.config/cloudphoto'
    user_config = user_config_dir + r'/cloudphotorc.ini'

    config['DEFAULT'] = {
        'aws_access_key_id': access_key_id,
        'aws_secret_access_key': secret_access_key,
        'bucket': bucket_name,
        'region': 'ru-central1',
        'endpoint_url': endpoint_url
    }

    with open(user_config, 'w') as configfile:
        config.write(configfile)


def init_session():
    user_config_dir = os.path.expanduser("~") + r'/.config/cloudphoto'
    user_config = user_config_dir + r'/cloudphotorc.ini'

    config = configparser.ConfigParser()
    config.read(user_config)

    aws_access_key_id = config['DEFAULT']['aws_access_key_id']
    aws_secret_access_key = config['DEFAULT']['aws_secret_access_key']
    endpoint_url = config['DEFAULT']['endpoint_url']
    region = config['DEFAULT']['region']
    bucket = config['DEFAULT']['bucket']

    YOS_ENDPOINT = endpoint_url
    s3BucketName = bucket

    uploader_session = boto3.session.Session()
    uploader_resource = uploader_session.resource(service_name='s3', endpoint_url=YOS_ENDPOINT)
    uploader_pub_bucket = uploader_resource.Bucket(s3BucketName)

    return {
        'uploader_session': uploader_session,
        'uploader_resource': uploader_resource,
        'uploader_pub_bucket': uploader_pub_bucket,
        'YOS_ENDPOINT': YOS_ENDPOINT,
        's3BucketName': s3BucketName,
        'region': region
    }


def list():
    config = init_session()

    bucket = config['uploader_pub_bucket']

    folders = set()

    for obj in bucket.objects.all():
        prefix, delimiter, _ = obj.key.rpartition('/')
        if prefix:
            folders.add(prefix)

    for folder in sorted(folders):
        print(folder)

    if len(folders) != 0:
        exit(0)

    if len(folders) == 0:
        print('Photo albums not found')
        exit(1)


# upload — отправка фотографий в облачное хранилище.
def upload(album, photo_dir):
    config = init_session()
    bucket = config['uploader_pub_bucket']

    file_names = []

    if not os.path.isdir(photo_dir):
        print('Warning: No such directory ' + photo_dir)
        exit(1)

    for path in os.listdir(photo_dir):
        if os.path.isfile(os.path.join(photo_dir, path)) & (".jpg" in path):
            file_names.append(path)

    if len(file_names) == 0:
        print('Warning: Photos not found in directory ' + photo_dir)
        exit(1)

    for file_name in file_names:
        try:
            uploader_object = bucket.Object(album + '/' + file_name)
            uploader_object.upload_file(photo_dir + '/' + file_name)

        except Exception:
            print('Warning: Photo not sent ' + file_name)
            pass

    exit(0)


def delete(album):
    config = init_session()
    bucket = config['uploader_pub_bucket']

    keys = []
    for file in bucket.objects.filter(Prefix=album + '/'):
        keys.append(file.key)

    if len(keys) == 0:
        print('Warning: Photo album not found ' + album)
        exit(1)

    for key in keys:
        bucket.delete_objects(Delete={
            'Objects': [
                {
                    'Key': key
                }
            ]
        })

    exit(0)


def mksite():
    config = init_session()
    bucket = config['uploader_pub_bucket']

    folders = set()

    for obj in bucket.objects.all():
        prefix, delimiter, _ = obj.key.rpartition('/')
        if prefix:
            folders.add(prefix)

    folders = sorted(folders)
    bucket_website = bucket.Website()

    bucket_website.put(WebsiteConfiguration={
        "IndexDocument": {
            "Suffix": "index.html"
        },
        "ErrorDocument": {
            "Key": "error.html"
        },
    })

    index_page_content = Path(r'C:\Users\Impl\Desktop\index.html').read_text(encoding='utf-8')
    soup = BeautifulSoup(index_page_content, 'html.parser')
    i = 0

    for folder in folders:
        i = i + 1
        tag = soup.new_tag("a", href='album' + str(i) + '.html')
        tag.string = 'альбом ' + folder
        soup.ul.append(tag)
        tag.wrap(soup.new_tag("li"))

    html_object = bucket.Object('index.html')
    html_object.put(Body=str(soup), ContentType='text/html')

    i = 0
    for folder in folders:
        i = i + 1

        album_page_content = Path(r"C:\Users\Impl\Desktop\album-page.html").read_text(encoding='utf-8')
        soup_page = BeautifulSoup(album_page_content, 'html.parser')

        for file in bucket.objects.filter(Prefix=folder):
            tag = soup_page.new_tag("img", src=file.key, attrs={'data-title': file.key})
            soup_page.div.append(tag)

            html_object = bucket.Object('album' + str(i) + '.html')
            html_object.put(Body=str(soup_page), ContentType='text/html')

    exit(0)
