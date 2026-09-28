"""Self-runner editorial moderation; Firebase Admin credentials required."""
import argparse
import json

from .firebase_sync import firebase


def main():
    parser = argparse.ArgumentParser(description='Inspect SENLIS reports and hide abusive messages')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('reports')
    sub.add_parser('corrections')
    hide = sub.add_parser('hide-message')
    hide.add_argument('room')
    hide.add_argument('message_id')
    resolve = sub.add_parser('resolve-report')
    resolve.add_argument('report_id')
    args = parser.parse_args()
    cloud = firebase()
    if args.command in ('reports', 'corrections'):
        for doc in cloud.collection(args.command).limit(100).stream():
            print(json.dumps({'id': doc.id, **doc.to_dict()}, ensure_ascii=False, default=str))
    elif args.command == 'hide-message':
        if args.room != 'global' and not (len(args.room) == 32 and
                                          all(ch in '0123456789abcdef' for ch in args.room)):
            raise SystemExit('Invalid room id')
        ref = cloud.collection('rooms').document(args.room).collection('messages').document(args.message_id)
        if not ref.get().exists:
            raise SystemExit('Message missing')
        ref.update({'status': 'hidden'})
        print('Message hidden')
    elif args.command == 'resolve-report':
        ref = cloud.collection('reports').document(args.report_id)
        if not ref.get().exists:
            raise SystemExit('Report missing')
        ref.update({'status': 'resolved'})
        print('Report resolved')


if __name__ == '__main__':
    main()
