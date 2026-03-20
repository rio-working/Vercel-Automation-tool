/**
 * Agenda.gs — Google Calendar 予定取得 + カレンダー一覧
 * CalendarApp を使用（サービスアカウント不要・ユーザー認証で動作）
 */

function getAgenda() {
  const today = new Date();
  const startOfDay = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 0, 0, 0);
  const endOfDay   = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 23, 59, 59);

  // 設定から選択済みカレンダーIDを取得
  let selectedIds = null;
  try {
    const settings = getSettingsMap();
    const raw = settings['calendar_selected_ids'];
    if (raw) selectedIds = JSON.parse(raw);
  } catch (e) {}

  // 取得対象カレンダーIDを収集
  let calIds = [];
  if (selectedIds && selectedIds.length > 0) {
    calIds = selectedIds;
  } else {
    const props = PropertiesService.getScriptProperties();
    const primaryId = props.getProperty('GOOGLE_CALENDAR_ID') || '';
    if (primaryId) calIds.push(primaryId);

    const extra = props.getProperty('GOOGLE_EXTRA_CALENDAR_IDS') || '';
    extra.split(',').forEach(id => {
      id = id.trim();
      if (id && !calIds.includes(id)) calIds.push(id);
    });

    CalendarApp.getAllCalendars().forEach(cal => {
      if (!calIds.includes(cal.getId())) calIds.push(cal.getId());
    });
  }

  const seenIds = {};
  const events = [];

  calIds.forEach(calId => {
    try {
      const cal = CalendarApp.getCalendarById(calId);
      if (!cal) return;
      cal.getEvents(startOfDay, endOfDay).forEach(event => {
        const eid = event.getId();
        if (seenIds[eid]) return;
        seenIds[eid] = true;

        const isAllDay = event.isAllDayEvent();
        let timeStr = '終日';
        let startIso = null;
        let endIso = null;
        if (!isAllDay) {
          const s = event.getStartTime();
          const eEnd = event.getEndTime();
          const h = s.getHours().toString().padStart(2, '0');
          const m = s.getMinutes().toString().padStart(2, '0');
          timeStr = h + ':' + m;
          startIso = s.toISOString();
          endIso = eEnd.toISOString();
        }
        events.push({
          id:          eid,
          title:       event.getTitle() || '（タイトルなし）',
          time:        timeStr,
          start:       startIso,
          end:         endIso,
          location:    event.getLocation() || '',
          description: event.getDescription() || '',
          all_day:     isAllDay,
          html_link:   event.getOriginalCalendarId
            ? 'https://calendar.google.com/calendar/r/day/' +
              today.getFullYear() + '/' + (today.getMonth() + 1) + '/' + today.getDate()
            : '',
          calendar_id: calId,
        });
      });
    } catch (e) {
      // アクセス不可のカレンダーはスキップ
    }
  });

  // 時刻順ソート（終日イベント先頭）
  events.sort((a, b) => {
    if (a.all_day && !b.all_day) return -1;
    if (!a.all_day && b.all_day) return 1;
    return (a.time || '').localeCompare(b.time || '');
  });

  return events;
}

function getCalendarLists() {
  const props = PropertiesService.getScriptProperties();
  const calIds = [];

  const primaryId = props.getProperty('GOOGLE_CALENDAR_ID') || '';
  if (primaryId) calIds.push(primaryId);

  const extra = props.getProperty('GOOGLE_EXTRA_CALENDAR_IDS') || '';
  extra.split(',').forEach(id => {
    id = id.trim();
    if (id && !calIds.includes(id)) calIds.push(id);
  });

  CalendarApp.getAllCalendars().forEach(cal => {
    if (!calIds.includes(cal.getId())) calIds.push(cal.getId());
  });

  return calIds.map(id => {
    try {
      const cal = CalendarApp.getCalendarById(id);
      return { id, summary: cal ? cal.getName() : id };
    } catch (e) {
      return { id, summary: id };
    }
  });
}

function createEvent(calendarId, title, startTime, endTime, location, description) {
  const cal = CalendarApp.getCalendarById(calendarId);
  const options = {};
  if (location) options.location = location;
  if (description) options.description = description;
  const event = cal.createEvent(title, new Date(startTime), new Date(endTime), options);
  return { id: event.getId(), title: event.getTitle() };
}

function updateEvent(calendarId, eventId, title, startTime, endTime, location, description) {
  const cal = CalendarApp.getCalendarById(calendarId);
  const event = cal.getEventById(eventId);
  if (title) event.setTitle(title);
  if (startTime && endTime) event.setTime(new Date(startTime), new Date(endTime));
  if (location !== undefined) event.setLocation(location || '');
  if (description !== undefined) event.setDescription(description || '');
  return { success: true };
}
