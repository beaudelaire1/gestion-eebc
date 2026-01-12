/**
 * More Menu Screen - Placeholder
 * Requirements: 6.1, 7.1, 10.1
 * Full implementation in Task 8.4
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation } from '@react-navigation/native';
import { MoreStackParamList } from '../../types/navigation';

type NavigationProp = NativeStackNavigationProp<MoreStackParamList, 'MoreMenu'>;

export const MoreMenuScreen: React.FC = () => {
  const navigation = useNavigation<NavigationProp>();

  const menuItems = [
    { title: 'Annonces', screen: 'Announcements' as const },
    { title: 'Dons', screen: 'Giving' as const },
    { title: 'Profil', screen: 'Profile' as const },
    { title: 'Paramètres', screen: 'Settings' as const },
  ];

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Plus</Text>
      {menuItems.map((item) => (
        <TouchableOpacity
          key={item.screen}
          style={styles.menuItem}
          onPress={() => navigation.navigate(item.screen)}
        >
          <Text style={styles.menuText}>{item.title}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    paddingTop: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    paddingHorizontal: 16,
  },
  menuItem: {
    backgroundColor: '#fff',
    paddingVertical: 16,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  menuText: {
    fontSize: 16,
  },
});
