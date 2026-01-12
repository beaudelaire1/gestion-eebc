/**
 * Giving Screen - Placeholder
 * Requirements: 7.1, 7.4
 * Full implementation in Task 15.1
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export const GivingScreen: React.FC = () => {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Dons</Text>
      <Text style={styles.subtitle}>Soutenir l'église</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
  },
});
