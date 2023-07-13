import argparse
from functions import list, upload, delete, init, mksite

parser = argparse.ArgumentParser(prog='cloudphoto')

command_parser = parser.add_subparsers(title='command', dest='command')

command_init = command_parser.add_parser('init', help='init connection')

command_list = command_parser.add_parser('list', help='list photo albums')

command_upload = command_parser.add_parser('upload', help='upload photos')
command_upload.add_argument('--album', dest='album', type=str, help='Photo album name', required=True)
command_upload.add_argument('--path', dest='photo_dir', type=str, default='.', help='Path to photos', required=False)

command_delete = command_parser.add_parser('delete', help='delete album')
command_delete.add_argument('--album', metavar='ALBUM', type=str, help='Photo album name')

command_mksite = command_parser.add_parser('mksite', help='start website')

args = parser.parse_args()

if args.command == 'init':
    aws_access_key_id = input('aws_access_key_id is ')
    aws_secret_access_key = input('aws_secret_access_key is ')
    bucket = input('bucket is ')

    init(aws_access_key_id, aws_secret_access_key, bucket)

elif args.command == 'list':
    list()

elif args.command == 'upload':
    upload(args.album, args.photo_dir)

elif args.command == 'delete':
    delete(args.album)

elif args.command == 'mksite':
    mksite()
