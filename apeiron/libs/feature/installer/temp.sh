#! /bin/bash
if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <base_folder> <subfolder1,subfolder2,...> <image_url>"
    exit 1
fi

# Parse the command-line arguments
base_folder=$1
image_url=$2
json_data=$3
nfs_server=$4
nfs_path=$5
hdd=$6
multinode=$7
serial_no=$8
hdd_name="ahv-metadata.img"



# Extract the image name from the URL
image_name=$(basename "$image_url")

# Create the base folder
mkdir -p "$base_folder"

# Download the image into the images folder
wget -P "$base_folder" "$image_url"

# Verify download
if [ -f "$base_folder/$image_name" ]; then
  echo "Image downloaded successfully to $base_folder/$image_name"
else
  echo "Failed to download image."
fi

#create metadata folder
mkdir -p "$base_folder/metadata"

#create file installer.json
json_string=$(echo $json_data | sed "s/'/\"/g")
echo $json_string

if [ $multinode == "yes" ];then
	mkdir -p "$base_folder/metadata/ACH12297H0R"
	touch "$base_folder/metadata/ACH12297H0R/installer.json"
	mkdir -p "$base_folder/metadata/BCH12297H0R"
	touch "$base_folder/metadata/BCH12297H0R/installer.json"
	mkdir -p "$base_folder/metadata/CCH12297H0R"
	touch "$base_folder/metadata/CCH12297H0R/installer.json"
	mkdir -p "$base_folder/metadata/$serial_no"
	#creating metadata inside right folder as per serial num
	inst_json_dest = "$base_folder/metadata/$serial_no"
	echo $json_string | jq '.' > "$base_folder/metadata/$serial_no/installer.json"
	echo "Setting executable permission to the json"
	chmod 777 $base_folder/metadata/$serial_no/installer.json
else
	echo $json_string | jq '.' > "$base_folder/metadata/installer.json"
	echo "Setting executable permission to the json"
	chmod 777 $base_folder/metadata/installer.json
fi

cd $base_folder

if [ $hdd == "yes" ];then
	echo "skipping customization as metadata would be served over HDD"
	echo "creating img file for HDD"
	fallocate -x -l 1M ahv-metadata.img
	mkfs.vfat -n AHV-META ahv-metadata.img
	mnt=$(mktemp -d)
	sudo mount ahv-metadata.img $mnt
	sudo cp -Rapv ./metadata/* $mnt
	sudo umount $mnt
else
	#prepare customized iso image
	echo "running the script from base folder"
	xorriso -dev $image_name -boot_image any keep -add ./metadata
fi

#copy images to NFS server
if [ $hdd == "yes" ];then
	echo "copying ISO image without metadata"
	sshpass -p nutanix/4u scp $image_name nutanix@$nfs_server:$nfs_path
	echo "copying HDD img file with meta data"
	sshpass -p nutanix/4u scp $hdd_name nutanix@$nfs_server:$nfs_path
else
	echo "copying customized image"
	sshpass -p nutanix/4u scp $image_name nutanix@$nfs_server:$nfs_path
fi
