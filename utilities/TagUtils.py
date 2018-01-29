def is_tag_in_tagset(tag,tagset):
    for value in tagset:
        if tag == value['Key']:
            return True
    else:
        return False