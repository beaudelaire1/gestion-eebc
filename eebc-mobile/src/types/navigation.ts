/**
 * Navigation type definitions for React Navigation
 */

export type RootStackParamList = {
  Auth: undefined;
  Main: undefined;
};

export type AuthStackParamList = {
  Login: undefined;
  ChangePassword: { mustChange: boolean };
};

export type MainTabParamList = {
  Dashboard: undefined;
  Members: undefined;
  Events: undefined;
  Worship: undefined;
  More: undefined;
};

export type MembersStackParamList = {
  MembersList: undefined;
  MemberDetail: { memberId: number };
};

export type EventsStackParamList = {
  EventsList: undefined;
  EventDetail: { eventId: number };
};

export type WorshipStackParamList = {
  WorshipList: undefined;
  ServiceDetail: { serviceId: number };
};

export type MoreStackParamList = {
  MoreMenu: undefined;
  Announcements: undefined;
  AnnouncementDetail: { announcementId: number };
  Giving: undefined;
  DonationForm: { donationType?: string };
  Profile: undefined;
  Settings: undefined;
};
