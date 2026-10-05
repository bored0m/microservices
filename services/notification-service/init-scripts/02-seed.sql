-- Тестовые шаблоны уведомлений
INSERT INTO notification_templates (code, subject_template, body_template) VALUES
('PAYMENT_SUCCESS',      'Платеж прошел успешно',  'Ваш платеж на сумму {{amount}} руб. успешно обработан.'),
('ISSUE_CREATED',        'Заявка принята',         'Ваша заявка №{{issue_id}} по адресу {{address}} принята в работу.'),
('ISSUE_STATUS_CHANGED', 'Статус заявки изменен',  'Статус вашей заявки №{{issue_id}} изменен на "{{status}}".'),
('PARKING_RESERVED',     'Парковка забронирована', 'Место на парковке {{parking_name}} забронировано до {{end_time}}.')
ON CONFLICT (code) DO NOTHING;