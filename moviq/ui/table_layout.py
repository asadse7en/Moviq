import os
from pathlib import Path


def fit_column_widths(available, minimums, weights):
    available = max(available, sum(minimums))
    extra = max(0, available - sum(minimums))
    total_weight = sum(weights)
    shares = [extra * weight / total_weight for weight in weights]
    widths = [
        minimum + int(share)
        for minimum, share in zip(minimums, shares)
    ]
    remainder = available - sum(widths)
    order = sorted(
        range(len(weights)),
        key=lambda index: shares[index] - int(shares[index]),
        reverse=True,
    )
    for index in order[:remainder]:
        widths[index] += 1
    return tuple(widths)


def folder_and_file(path):
    path = Path(path)
    return os.path.join(path.parent.name, path.name)


def source_path_display(path, root):
    path, root = Path(path), Path(root)
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def target_name_display(target):
    target = Path(target)
    return folder_and_file(target)


def tv_target_name_display(target):
    target = Path(target)
    return os.path.join(
        target.parent.parent.name,
        target.parent.name,
        target.name,
    )
