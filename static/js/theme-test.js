/**
 * Script de test pour le système de thèmes EEBC
 * À utiliser uniquement en développement
 */

// Test de fonctionnement du système de thèmes
function testThemeSystem() {
    console.log('🎨 Test du système de thèmes EEBC');
    
    // Vérifier que le gestionnaire de thème est chargé
    if (typeof themeManager === 'undefined') {
        console.error('❌ ThemeManager non chargé');
        return false;
    }
    
    console.log('✅ ThemeManager chargé');
    
    // Vérifier les thèmes disponibles
    const expectedThemes = ['light', 'dark', 'flat', 'neon', 'ocean', 'sunset', 'forest'];
    const availableThemes = themeManager.themes.map(t => t.id);
    
    console.log('📋 Thèmes disponibles:', availableThemes);
    
    const missingThemes = expectedThemes.filter(theme => !availableThemes.includes(theme));
    if (missingThemes.length > 0) {
        console.error('❌ Thèmes manquants:', missingThemes);
        return false;
    }
    
    console.log('✅ Tous les thèmes sont disponibles');
    
    // Tester l'application de chaque thème
    console.log('🔄 Test d\'application des thèmes...');
    
    expectedThemes.forEach((themeId, index) => {
        setTimeout(() => {
            themeManager.applyTheme(themeId);
            console.log(`✅ Thème "${themeId}" appliqué`);
            
            // Vérifier que l'attribut data-theme est correctement défini
            const currentTheme = document.documentElement.getAttribute('data-theme');
            if (currentTheme === themeId) {
                console.log(`✅ Attribut data-theme correctement défini: ${currentTheme}`);
            } else {
                console.error(`❌ Erreur d'attribut data-theme. Attendu: ${themeId}, Reçu: ${currentTheme}`);
            }
            
            // Tester les variables CSS
            const computedStyle = getComputedStyle(document.documentElement);
            const primaryColor = computedStyle.getPropertyValue('--accent-primary').trim();
            
            if (primaryColor) {
                console.log(`✅ Variable CSS --accent-primary: ${primaryColor}`);
            } else {
                console.error('❌ Variable CSS --accent-primary non définie');
            }
            
        }, index * 1000);
    });
    
    // Revenir au thème par défaut après les tests
    setTimeout(() => {
        themeManager.applyTheme('light');
        console.log('🔄 Retour au thème par défaut');
        console.log('✅ Tests terminés avec succès !');
    }, expectedThemes.length * 1000 + 1000);
    
    return true;
}

// Test des couleurs de thème
function testThemeColors() {
    console.log('🎨 Test des couleurs de thème');
    
    const themes = ['light', 'dark', 'flat', 'neon', 'ocean', 'sunset', 'forest'];
    
    themes.forEach(themeId => {
        // Appliquer temporairement le thème
        document.documentElement.setAttribute('data-theme', themeId);
        
        const colors = themeManager.getThemeColors();
        console.log(`🎨 Couleurs du thème "${themeId}":`, colors);
        
        // Vérifier que toutes les couleurs sont définies
        const requiredColors = ['primary', 'success', 'warning', 'danger', 'info', 'background', 'text'];
        const missingColors = requiredColors.filter(color => !colors[color] || colors[color] === '');
        
        if (missingColors.length > 0) {
            console.error(`❌ Couleurs manquantes pour le thème "${themeId}":`, missingColors);
        } else {
            console.log(`✅ Toutes les couleurs définies pour le thème "${themeId}"`);
        }
    });
}

// Test du sélecteur de thème
function testThemeSelector() {
    console.log('🎛️ Test du sélecteur de thème');
    
    // Ouvrir le sélecteur
    themeManager.showThemeSelector();
    
    setTimeout(() => {
        const selector = document.getElementById('themeSelector');
        if (selector && selector.classList.contains('theme-selector--visible')) {
            console.log('✅ Sélecteur de thème ouvert');
            
            // Vérifier que toutes les options sont présentes
            const options = selector.querySelectorAll('.theme-option');
            if (options.length === 7) {
                console.log('✅ Toutes les options de thème sont présentes');
            } else {
                console.error(`❌ Nombre d'options incorrect. Attendu: 7, Reçu: ${options.length}`);
            }
            
            // Fermer le sélecteur
            setTimeout(() => {
                themeManager.hideThemeSelector();
                console.log('✅ Sélecteur de thème fermé');
            }, 2000);
            
        } else {
            console.error('❌ Sélecteur de thème non ouvert');
        }
    }, 500);
}

// Test de persistance
function testThemePersistence() {
    console.log('💾 Test de persistance des thèmes');
    
    const originalTheme = themeManager.currentTheme;
    const testTheme = 'neon';
    
    // Appliquer un thème de test
    themeManager.applyTheme(testTheme);
    
    // Vérifier que le thème est sauvegardé
    const savedTheme = localStorage.getItem('eebc-theme');
    if (savedTheme === testTheme) {
        console.log('✅ Thème sauvegardé dans localStorage');
    } else {
        console.error(`❌ Erreur de sauvegarde. Attendu: ${testTheme}, Reçu: ${savedTheme}`);
    }
    
    // Simuler un rechargement en recréant le gestionnaire
    setTimeout(() => {
        const newManager = new ThemeManager();
        if (newManager.currentTheme === testTheme) {
            console.log('✅ Thème restauré après rechargement simulé');
        } else {
            console.error(`❌ Erreur de restauration. Attendu: ${testTheme}, Reçu: ${newManager.currentTheme}`);
        }
        
        // Restaurer le thème original
        themeManager.applyTheme(originalTheme);
    }, 1000);
}

// Fonction principale de test
function runAllTests() {
    console.log('🚀 Démarrage des tests du système de thèmes EEBC');
    console.log('=====================================');
    
    if (!testThemeSystem()) {
        console.error('❌ Tests échoués - Arrêt');
        return;
    }
    
    setTimeout(() => {
        testThemeColors();
    }, 8000);
    
    setTimeout(() => {
        testThemeSelector();
    }, 10000);
    
    setTimeout(() => {
        testThemePersistence();
    }, 15000);
    
    setTimeout(() => {
        console.log('=====================================');
        console.log('🎉 Tous les tests terminés !');
        console.log('Vous pouvez maintenant utiliser le système de thèmes normalement.');
    }, 18000);
}

// Exposer les fonctions de test globalement (uniquement en développement)
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    window.testThemeSystem = testThemeSystem;
    window.testThemeColors = testThemeColors;
    window.testThemeSelector = testThemeSelector;
    window.testThemePersistence = testThemePersistence;
    window.runAllTests = runAllTests;
    
    console.log('🔧 Fonctions de test disponibles:');
    console.log('- testThemeSystem()');
    console.log('- testThemeColors()');
    console.log('- testThemeSelector()');
    console.log('- testThemePersistence()');
    console.log('- runAllTests() - Lance tous les tests');
}