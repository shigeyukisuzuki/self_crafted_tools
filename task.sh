#!/usr/bin/bash
if [ "$1" = "push" ]; then
	if [ "$2" = "--no-dry" ]; then
		rsync -av ~/task/ ssuzuki@"${taskServer}":~/task --update --delete
	else
		rsync -av ~/task/ ssuzuki@"${taskServer}":~/task --update --delete --dry-run
	fi
elif [ "$1" = "pull" ]; then
	if [ "$2" = "--no-dry" ]; then
		rsync -av ssuzuki@"${taskServer}":~/task/ ~/task --update --delete
	else
		rsync -av ssuzuki@"${taskServer}":~/task/ ~/task --update --delete --dry-run
	fi
else
	echo "usage:"
	echo "task push [--no-dry]"
	echo "task pull [--no-dry]"
fi
