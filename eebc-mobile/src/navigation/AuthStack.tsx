/**
 * Auth Stack Navigator - Login and ChangePassword screens
 * Requirements: 1.1, 1.5
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { AuthStackParamList } from '../types/navigation';
import { LoginScreen, ChangePasswordScreen } from '../screens';
import { useAuthStore } from '../stores/authStore';

const Stack = createNativeStackNavigator<AuthStackParamList>();

export const AuthStack: React.FC = () => {
  const { mustChangePassword } = useAuthStore();

  return (
    <Stack.Navigator
      initialRouteName={mustChangePassword ? 'ChangePassword' : 'Login'}
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
        name="Login"
        component={LoginScreen}
        options={{
          headerShown: false,
        }}
      />
      <Stack.Screen
        name="ChangePassword"
        component={ChangePasswordScreen}
        initialParams={{ mustChange: mustChangePassword }}
        options={{
          title: 'Changer le mot de passe',
          headerBackVisible: !mustChangePassword,
        }}
      />
    </Stack.Navigator>
  );
};
