/**
 * Members Stack Navigator - Navigation for member directory
 * Requirements: 3.1, 3.3
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { MembersStackParamList } from '../types/navigation';
import { MembersListScreen } from '../screens/members/MembersListScreen';
import { MemberDetailScreen } from '../screens/members/MemberDetailScreen';

const Stack = createNativeStackNavigator<MembersStackParamList>();

export const MembersStack: React.FC = () => {
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
        name="MembersList"
        component={MembersListScreen}
        options={{
          title: 'Annuaire',
          headerShown: false, // Tab navigator shows header
        }}
      />
      <Stack.Screen
        name="MemberDetail"
        component={MemberDetailScreen}
        options={{
          title: 'Profil',
        }}
      />
    </Stack.Navigator>
  );
};
