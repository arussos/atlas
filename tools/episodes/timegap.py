"""
M4.2a — Feature deterministica del time-gap tra due messaggi consecutivi
del current path.

I confini dei bucket sono intervalli semiaperti esatti, come da
docs/M4.2A_DETERMINISTIC_BOUNDARY_CANDIDATES.md, sezione time-gap. Il time
gap è una feature, mai una regola di boundary a sé stante — vedi la
conclusione della sezione corpus/time-gap in quel documento.

NOTA (Gold Pilot 001, freeze M4.2a): sui dati reali i gap temporali lunghi
sono risultati fortemente informativi ma non sufficienti da soli — due
boundary veri sono avvenuti entro un minuto. Vedi la sezione "Time gap
finding" della documentazione. Bucket e soglie non sono stati modificati
in questa passata.
"""

from typing import Optional, Tuple

TIME_GAP_BUCKET_LT_1M = "LT_1M"
TIME_GAP_BUCKET_1M_5M = "1M_5M"
TIME_GAP_BUCKET_5M_15M = "5M_15M"
TIME_GAP_BUCKET_15M_30M = "15M_30M"
TIME_GAP_BUCKET_30M_1H = "30M_1H"
TIME_GAP_BUCKET_1H_3H = "1H_3H"
TIME_GAP_BUCKET_3H_12H = "3H_12H"
TIME_GAP_BUCKET_12H_1D = "12H_1D"
TIME_GAP_BUCKET_1D_7D = "1D_7D"
TIME_GAP_BUCKET_GE_7D = "GE_7D"
TIME_GAP_BUCKET_UNKNOWN = "UNKNOWN"

# (upper_bound_exclusive_seconds, bucket_name), valutati in ordine; vince
# il primo limite di cui il gap è strettamente minore:
#   LT_1M      : gap < 60
#   1M_5M      : 60 <= gap < 300
#   5M_15M     : 300 <= gap < 900
#   15M_30M    : 900 <= gap < 1800
#   30M_1H     : 1800 <= gap < 3600
#   1H_3H      : 3600 <= gap < 10800
#   3H_12H     : 10800 <= gap < 43200
#   12H_1D     : 43200 <= gap < 86400
#   1D_7D      : 86400 <= gap < 604800
#   GE_7D      : gap >= 604800 (nessun limite superiore, gestito dopo il loop)
_BUCKET_THRESHOLDS = (
    (60, TIME_GAP_BUCKET_LT_1M),
    (300, TIME_GAP_BUCKET_1M_5M),
    (900, TIME_GAP_BUCKET_5M_15M),
    (1800, TIME_GAP_BUCKET_15M_30M),
    (3600, TIME_GAP_BUCKET_30M_1H),
    (10800, TIME_GAP_BUCKET_1H_3H),
    (43200, TIME_GAP_BUCKET_3H_12H),
    (86400, TIME_GAP_BUCKET_12H_1D),
    (604800, TIME_GAP_BUCKET_1D_7D),
)


def _is_valid_timestamp(value: object) -> bool:
    # bool è una sottoclasse di int in Python; un booleano JSON non è un
    # timestamp valido anche se isinstance(True, int) è True.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def compute_time_gap(
    before_created_at: Optional[float], after_created_at: Optional[float]
) -> Tuple[Optional[float], str]:
    """
    Restituisce (time_gap_seconds, time_gap_bucket).

    time_gap_seconds è None e il bucket è UNKNOWN ogni volta che uno dei
    due timestamp è mancante/non valido, oppure after_created_at <
    before_created_at.
    """
    if not _is_valid_timestamp(before_created_at) or not _is_valid_timestamp(after_created_at):
        return None, TIME_GAP_BUCKET_UNKNOWN

    gap = after_created_at - before_created_at
    if gap < 0:
        return None, TIME_GAP_BUCKET_UNKNOWN

    for upper_bound, bucket in _BUCKET_THRESHOLDS:
        if gap < upper_bound:
            return gap, bucket
    return gap, TIME_GAP_BUCKET_GE_7D
