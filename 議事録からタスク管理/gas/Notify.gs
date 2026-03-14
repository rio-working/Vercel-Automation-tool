/**
 * Notify.gs — Slack Webhook + MailApp 通知
 */

/**
 * 処理完了通知（Slack + メール）
 */
function sendNotifications(meetingId, summary) {
  const props = PropertiesService.getScriptProperties();
  const slackUrl = props.getProperty('SLACK_WEBHOOK_URL');
  const notifyEmail = props.getProperty('NOTIFY_EMAIL');

  const message = `🎙️ *議事録が完成しました*\n会議ID: ${meetingId}\n\n${summary || '（要約なし）'}`;

  if (slackUrl) {
    sendSlack(slackUrl, message);
  }
  if (notifyEmail) {
    sendEmail(notifyEmail, '議事録が完成しました', message.replace(/\*/g, ''));
  }
}

function sendSlack(webhookUrl, message) {
  try {
    UrlFetchApp.fetch(webhookUrl, {
      method: 'POST',
      contentType: 'application/json',
      payload: JSON.stringify({ text: message }),
      muteHttpExceptions: true,
    });
    logSheet('INFO', 'sendSlack', 'Slack通知送信完了');
  } catch (e) {
    logSheet('WARN', 'sendSlack', `Slack送信エラー: ${e}`);
  }
}

function sendEmail(to, subject, body) {
  try {
    MailApp.sendEmail(to, subject, body);
    logSheet('INFO', 'sendEmail', `メール送信完了: ${to}`);
  } catch (e) {
    logSheet('WARN', 'sendEmail', `メール送信エラー: ${e}`);
  }
}
