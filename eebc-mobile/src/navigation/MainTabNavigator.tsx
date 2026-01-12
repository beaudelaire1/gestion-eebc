/**
 * Main Tab Navigator - Bottom tab navigation for authenticated users
 * Requirements: 2.1
 */

import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import { MainTabParamList } from '../types/navigation';
import {
  DashboardScreen,
} from '../screens';
import { MembersStack } from './MembersStack';
import { EventsStack } from './EventsStack';
import { WorshipStack } from './WorshipStack';
import { MoreStack } from './MoreStack';

const Tab = createBottomTabNavigator<MainTabParamList>();

type IconName = keyof typeof Ionicons.glyphMap;

const getTabIcon = (routeName: string, focused: boolean): IconName => {
  const icons: Record<string, { focused: IconName; unfocused: IconName }> = {
    Dashboard: { focused: 'home', unfocused: 'home-outline' },
    Members: { focused: 'people', unfocused: 'people-outline' },
    Events: { focused: 'calendar', unfocused: 'calendar-outline' },
    Worship: { focused: 'musical-notes', unfocused: 'musical-notes-outline' },
    More: { focused: 'menu', unfocused: 'menu-outline' },
  };

  const icon = icons[routeName];
  return focused ? icon.focused : icon.unfocused;
};

export const MainTabNavigator: React.FC = () => {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          const iconName = getTabIcon(route.name, focused);
          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#3498db',
        tabBarInactiveTintColor: '#95a5a6',
        headerStyle: {
          backgroundColor: '#3498db',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      })}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          title: 'Accueil',
          tabBarLabel: 'Accueil',
        }}
      />
      <Tab.Screen
        name="Members"
        component={MembersStack}
        options={{
          title: 'Annuaire',
          tabBarLabel: 'Annuaire',
          headerShown: false,
        }}
      />
      <Tab.Screen
        name="Events"
        component={EventsStack}
        options={{
          title: 'Événements',
          tabBarLabel: 'Événements',
          headerShown: false,
        }}
      />
      <Tab.Screen
        name="Worship"
        component={WorshipStack}
        options={{
          title: 'Culte',
          tabBarLabel: 'Culte',
          headerShown: false,
        }}
      />
      <Tab.Screen
        name="More"
        component={MoreStack}
        options={{
          title: 'Plus',
          tabBarLabel: 'Plus',
          headerShown: false,
        }}
      />
    </Tab.Navigator>
  );
};
