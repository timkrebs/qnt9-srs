import { apiRequest } from './client'

export interface NotificationPreferences {
  email_notifications: boolean
  product_updates: boolean
  usage_alerts: boolean
  security_alerts: boolean
  marketing_emails: boolean
}

export interface NotificationPreferencesUpdate {
  email_notifications?: boolean
  product_updates?: boolean
  usage_alerts?: boolean
  security_alerts?: boolean
  marketing_emails?: boolean
}

export interface MessageResponse {
  message: string
  success: boolean
}

export const notificationService = {
  getPreferences: async (): Promise<NotificationPreferences> => {
    const response = await apiRequest<NotificationPreferences>(
      'notifications',
      '/api/v1/preferences',
      {
        method: 'GET',
      },
    )
    return response
  },

  updatePreferences: async (
    preferences: NotificationPreferencesUpdate,
  ): Promise<MessageResponse> => {
    const response = await apiRequest<MessageResponse>(
      'notifications',
      '/api/v1/preferences',
      {
        method: 'PATCH',
        body: JSON.stringify(preferences),
      },
    )
    return response
  },
}
