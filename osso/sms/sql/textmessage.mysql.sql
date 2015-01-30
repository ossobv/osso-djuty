-- vim: set ts=8 sts=4 sw=4 et noai syn=mysql:
ALTER TABLE sms_textmessage CHANGE COLUMN body_count body_count TINYINT UNSIGNED NOT NULL DEFAULT 1;
