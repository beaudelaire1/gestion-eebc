/**
 * Events Stack Navigator - Navigation for events and calendar
 * Requirements: 4.1, 4.3
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { EventsStackParamList } from '../types/navigation';
import { EventsScreen } from '../screens/events/EventsScreen';
import { EventDetailScreen } from '../screens/events/EventDetailScreen';

const Stack = createNativeStackNavigator<EventsStackParamList>();

export const EventsStack: React.FC = () => {
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
        name="EventsList"
        component={EventsScreen}
        options={{
          title: 'Événements',
          headerShown: false, // Tab navigator shows header
        }}
      />
      <Stack.Screen
        name="EventDetail"
        component={EventDetailScreen}
        options={{
          title: 'Détails',
        }}
      />
    </Stack.Navigator>
  );
};
