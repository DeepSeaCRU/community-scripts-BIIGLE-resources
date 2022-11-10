from tqdm import tqdm
import pandas as pd

import utils_pascalVOC


def add_label(name, label_tree_id, api):
    """
    Add a missing label to the label tree. Default color red
    :param name: new label name
    :param label_tree_id: label tree id
    :param api: biigle api object
    :return:
    """
    post_data = {
        'name': name,
        'color': "#FF0000"  # default color: red
    }
    p = api.post('label-trees/{}/labels'.format(label_tree_id), json=post_data)
    label_id = p.json()[0]["id"]
    return label_id


def create_label_index(api, label_tree_id, path_classes):
    """
    Return a table with biigle label ids, create labels if missing
    :param api: biigle api object
    :param label_tree_id: label tree id
    :param path_classes: path to a list of classes
    :return:
    """
    with open(path_classes, 'r') as f:
        classes = f.read().splitlines()

    # label_index creator
    label_tree = api.get('label-trees/{}'.format(label_tree_id)).json()
    labels = label_tree['labels']
    label_idx = []
    for i in classes:
        added = False
        for label in labels:
            if label['name'] == i:
                label_idx.append([label['name'], label['id']])
                added = True
        if not added:
            print("Error: missing label in label tree !! Adding missing label: " + str(i))
            label_id = add_label(i, label_tree_id, api)
            label_idx.append([i, label_id])
    return label_idx


def create_image_index(api, volume_id):
    """
    Returns a table with volume images biigle ids
    :param api: Biigle api object
    :param volume_id: volume id
    :return:
    """
    image_ids = api.get('volumes/{}/files'.format(volume_id)).json()
    biigle_images = []
    for image_id in tqdm(image_ids):
        image_info = api.get('images/{}'.format(image_id)).json()
        biigle_images.append([image_info["filename"], image_info['id']])
    biigle_images_df = pd.DataFrame(biigle_images, columns=['name', 'id'])
    return biigle_images_df


def pascalVOC_to_biigle(image_name, pascalVOC_path, label_idx, images_idx, shape, api):
    """
    Read the pascalVOC xml file and import annotations to biigle
    :param image_name: image name (with suffix .jpg or .png)
    :param pascalVOC_path: path to an .xml pascalVOC file
    :param label_idx: label index, from create_label_index
    :param images_idx: image index, from create_image_index
    :param shape: shape. "Rectangle" or "Circle"
    :param api: biigle api object
    :return: 1 if success
    """
    shapes_id = {"Circle": 4,
                 "Rectangle": 5,
                 }

    image_id = int(images_idx.loc[images_idx['name'] == image_name]['id'])  # Image Biigle id

    annotations = utils_pascalVOC.read_pascalVOC_content(pascalVOC_path)  # Get annotations from pascalVOC

    post_data = {
        'shape_id': shapes_id[shape],
        'label_id': 0,
        'confidence': 1,
        'points': [],
    }
    for index, row in annotations.iterrows():  # For each annotation
        # Prepare annotations coordinates
        if shape == "Circle":
            width = row['xmax'] - row['xmin']
            height = row['ymax'] - row['ymin']
            x = row['xmin'] + (width / 2)
            y = row['ymin'] + (height / 2)
            points = [int(x), int(y), int(max(width, height))]
        elif shape == "Rectangle":
            points = [int(row["xmin"]), int(row["ymin"]), int(row["xmax"]), int(row["ymin"]), int(row["xmax"]),
                      int(row["ymax"]), int(row["xmin"]), int(row["ymax"])]

        for label in label_idx:
            if label[0] == row["name"]:
                post_data['label_id'] = label[1]  # Get label biigle id
        post_data['points'] = points
        post_data['confidence'] = float(row["confidence"])
        p = api.post('images/{}/annotations'.format(image_id), json=post_data)  # Post payload to biigle
    return 1
