// Endpoints del servicio app-users (/users).
// Strings fijos o funciones que construyen la ruta; se concatenan a BASE_URL en apiCall.
export const USERS_ENDPOINTS = {
  // auth route
  AUTH_LOGIN: "/users/auth/login",
  AUTH_RECOVERY: "/users/auth/recovery",
  AUTH_RECOVERY_CODE: "/users/auth/recovery-code",
  AUTH_ME: "/users/auth/me",
  AUTH_LOGOUT: "/users/auth/logout",
  // user route
  USER_REGISTER: "/users/user/register",
  USERS: "/users/user/all",
  USER_ADMIN_UPDATE: (user_id: number) => `/users/user/${user_id}`,
  USER_RESEND_PASSWORD: (user_id: number) =>
    `/users/user/resend-password/${user_id}`,
  PASSWORD_CHANGE: "/users/user/password-change",
  USER_UPDATE: "/users/user/update-user",
  USER_LOG: "/users/user/log",
  // role route
  ROL_LIST: "/users/role/all",
  ROLES: "/users/role/all", // Alias de ROL_LIST
  PERMISSIONS: "/users/role/permissions",
  ROL_PERMISSIONS: "/users/role/role-permissions",
  VERIFY_PERMISSION: "/users/role/permission/verify",
  ROL_ADD: "/users/role/add",
  ROL_UPDATE: (rol_id: number | string) => `/users/role/update/${rol_id}`,
  ROL_DELETE: (rol_id: number | string) => `/users/role/delete/${rol_id}`,
  PERMISSION_ADD: "/users/role/permission/add",
  PERMISSION_UPDATE: (permission_id: string) =>
    `/users/role/permission/update/${permission_id}`,
  PERMISSION_DELETE: (permission_id: string) =>
    `/users/role/permission/delete/${permission_id}`,
  // notification route
  NOTIFICATION_STREAM: "/users/notification/stream",
  NOTIFICATION_CREATE: "/users/notification/add",
  NOTIFICATION_DELETE: (noti_id: number) => `/users/notification/${noti_id}`,
  NOTIFICATION_DELETE_ALL: "/users/notification/delete-all",
  NOTIFICATION_LINKED: (linked_id: string) =>
    `/users/notification/linked/${linked_id}`,
};
