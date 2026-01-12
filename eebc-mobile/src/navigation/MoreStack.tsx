/**
 * More Stack Navigator - Announcements, Giving, Profile, Settings
 * Requirements: 6.1, 7.1, 10.1
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { MoreStackParamList } from '../types/navigation';
import {
  MoreMenuScreen,
  AnnouncementsScreen,
  GivingScreen,
  ProfileScreen,
  SettingsScreen,
} from '../screens';

const Stack = createNativeStackNavigator<MoreStackParamList>();

export const MoreStack: React.FC = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: '#3498db',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      }}
    >
      <Stack.Screen
        name="MoreMenu"
        component={MoreMenuScreen}
        options={{
          title: 'Plus',
        }}
      />
      <Stack.Screen
        name="Announcements"
        component={AnnouncementsScreen}
        options={{
          title: 'Annonces',
        }}
      />
      <Stack.Screen
        name="Giving"
        component={GivingScreen}
        options={{
          title: 'Dons',
        }}
      />
      <Stack.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          title: 'Profil',
        }}
      />
      <Stack.Screen
        name="Settings"
        component={SettingsScreen}
        options={{
          title: 'Paramètres',
        }}
      />
    </Stack.Navigator>
  );
};
