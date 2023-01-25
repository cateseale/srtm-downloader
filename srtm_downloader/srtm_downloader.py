import time
import ee


def _check_task_completed(task_id):
    """
    Returns True if a task export completes successfully, else returns false.
    Inputs:
        task_id (str): Google Earth Engine task id
    Returns:
        boolean
    """
    status = ee.data.getTaskStatus(task_id)[0]
    if status["state"] in (ee.batch.Task.State.CANCELLED, ee.batch.Task.State.FAILED):
        if "error_message" in status:
            print(status["error_message"])
        return True
    elif status["state"] == ee.batch.Task.State.COMPLETED:
        return True
    return False


def wait_for_tasks(task_ids=[], timeout=3600):
    """
    Wait for tasks to complete, fail, or timeout
    Waits for all active tasks if task_ids is not provided
    Note: Tasks will not be canceled after timeout, and
    may continue to run.
    Inputs:
        task_ids (list):
        timeout (int):
    Returns:
        None
    """
    start = time.time()
    elapsed = 0
    while elapsed < timeout or timeout == 0:
        elapsed = time.time() - start
        finished = [_check_task_completed(task) for task in task_ids]
        if all(finished):
            print(f"Tasks {task_ids} completed after {elapsed}s")
            return True
        time.sleep(5)
    print(f"Stopped waiting for {len(task_ids)} tasks after {timeout} seconds")
    return False


def get_srtm_data(resolution=30):
    """

    :param resolution:
    :return:
    """
    valid_resolutions = [30, 90]

    if resolution not in valid_resolutions:
        raise ValueError(
            "SRTM resolution is only available in 30m or 90m resolution. Please use resolution=30 or "
            "resolution=90"
        )

    if resolution == 30:
        srtm = ee.Image("USGS/SRTMGL1_003")
        return srtm

    if resolution == 90:
        srtm = ee.Image("CGIAR/SRTM90_V4")
        return srtm


def get_elevation(srtm, aoi):
    elev = srtm.select("elevation").clip(aoi)
    return elev


def get_slope(srtm, aoi):
    slope = ee.Terrain.slope(get_elevation(srtm, aoi)).clip(aoi)
    return slope


def get_aspect(srtm, aoi):
    aspect = ee.Terrain.aspect(get_elevation(srtm, aoi)).clip(aoi)
    return aspect


def get_hillshade(srtm, aoi):
    hillshade = ee.Terrain.hillshade(get_elevation(srtm, aoi), 315, 45).clip(aoi)
    return hillshade


def derive_srtm_data(aoi, resolution=30):
    srtm_data = get_srtm_data(resolution)

    srtm_elev = get_elevation(srtm_data, aoi)
    srtm_slope = get_slope(srtm_data, aoi)
    srtm_aspect = get_aspect(srtm_data, aoi)
    srtm_hillshade = get_hillshade(srtm_data, aoi)

    return srtm_elev, srtm_slope, srtm_aspect, srtm_hillshade


def export_image(export_str, image, aoi, crs, resolution, no_data):
    task = ee.batch.Export.image.toDrive(
        image=image.unmask(no_data),
        description=f"export_{export_str}_{resolution}",
        scale=resolution,
        region=aoi,
        fileNamePrefix=f"{export_str}_{resolution}",
        crs=crs,
        fileFormat="GeoTIFF",
        maxPixels=1e13,
    )

    task.start()
    print("Exporting: Task id ", task.id)
    wait_for_tasks([task.id])


def export_srtm_data(
    aoi,
    resolution=30,
    export="elevation",
    crs="EPSG:4326",
    no_data=0,
    elevation_no_data=32767,
):

    valid_exports = ["elevation", "slope", "aspect", "hillshade"]
    if export not in valid_exports:
        raise ValueError(
            "Invalid export choice. Valid export options are 'elevation', 'slope', 'aspect', 'hillshade'"
        )

    elev, slope, aspect, shade = derive_srtm_data(aoi, resolution)

    if export == "elevation":
        export_image(export, elev, aoi, crs, resolution, elevation_no_data)

    elif export == "slope":
        export_image(export, slope, aoi, crs, resolution, no_data)

    elif export == "aspect":
        export_image(export, aspect, aoi, crs, resolution, no_data)

    elif export == "hillshade":
        export_image(export, shade, aoi, crs, resolution, no_data)


if __name__ == "__main__":
    ee.Initialize()

    region = ee.Geometry.Polygon(
        [[[-85.93, 16.08], [-85.93, 15.69], [-85.40, 15.69], [-85.40, 16.08]]]
    )

    export_srtm_data(aoi=region, resolution=30, export="hillshade")
