/**
 * Worship Stack Navigator - Navigation for worship-related screens
 * Requirements: 5.3
 */

import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import { WorshipScreen, ServiceDetailScreen } from '../screens';

export type WorshipStackParamList = {
  WorshipList: undefined;
  ServiceDetail: { serviceId: number };
};

const Stack = createStackNavigator<WorshipStackParamList>();

export const WorshipStack: React.FC = () => {
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
        name="WorshipList"
        component={WorshipScreen}
        options={{
          title: 'Culte',
        }}
      />
      <Stack.Screen
        name="ServiceDetail"
        component={ServiceDetailScreen}
        options={{
          title: 'Détails du service',
        }}
      />
    </Stack.Navigator>
  );
};