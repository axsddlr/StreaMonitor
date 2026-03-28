"""Helpers to serialize Bot instances and system state to DTOs."""
from streamonitor.managers.outofspace_detector import OOSDetector
from streamonitor.utils.human_file_size import human_file_size
from .schemas import StreamerDTO, DiskSpaceDTO


def streamer_to_dto(streamer) -> StreamerDTO:
    return StreamerDTO(
        username=streamer.username,
        site=streamer.site,
        siteslug=streamer.siteslug,
        running=streamer.running,
        recording=streamer.recording,
        status_code=streamer.sc.value,
        status_text=streamer.status(),
        url=streamer.url,
        gender=streamer.gender.value if hasattr(streamer.gender, 'value') else streamer.gender,
        country=streamer.country,
        country_flag=streamer.country_data.get('flag', ''),
        country_name=streamer.country_data.get('name', ''),
        video_count=len(streamer.video_files),
        video_total_size=streamer.video_files_total_size,
    )


def disk_space_dto() -> DiskSpaceDTO:
    usage = OOSDetector.space_usage()
    percentage = round(usage.free / usage.total * 100, 3) if usage.total > 0 else 0.0
    return DiskSpaceDTO(
        free=usage.free,
        total=usage.total,
        free_human=human_file_size(usage.free),
        total_human=human_file_size(usage.total),
        percentage_free=percentage,
    )
