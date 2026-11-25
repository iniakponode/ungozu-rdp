const EVENT_TIME_ZONE = 'Africa/Lagos'

export function watInputToUtcIso(value: string): string | null {
  // datetime-local values contain no timezone.
  // Interpret them explicitly as West Africa Time (UTC+01:00).
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) {
    return null
  }

  const date = new Date(`${value}:00+01:00`)

  if (Number.isNaN(date.getTime())) return null

  // Reject normalized invalid dates such as 31 February.
  const reconstructed = new Date(date.getTime() + 60 * 60 * 1000)
    .toISOString()
    .slice(0, 16)

  if (reconstructed !== value) return null

  return date.toISOString()
}

export function parseRdpEventTimestamp(value: string): Date | null {
  const timestamp = value.trim()

  if (!timestamp) return null

  // Existing API/database convention: timezone-free values represent UTC.
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(timestamp)
  const date = new Date(hasTimezone ? timestamp : `${timestamp}Z`)

  return Number.isNaN(date.getTime()) ? null : date
}

export function eventTimestampToWatInput(
  value: string
): string | null {
  const date = parseRdpEventTimestamp(value)
  if (!date) return null

  return new Date(date.getTime() + 60 * 60 * 1000)
    .toISOString()
    .slice(0, 16)
}

export function formatRdpEventTime(value: string): string {
  const date = parseRdpEventTimestamp(value)

  if (!date) return 'Date unavailable'

  return (
    new Intl.DateTimeFormat('en-GB', {
      timeZone: EVENT_TIME_ZONE,
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(date) + ' WAT'
  )
}
