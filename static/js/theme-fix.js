/**
 * Script de correction pour les thèmes EEBC
 * Nettoie les anciennes clés localStorage et force la réapplication
 */

(function() {
    console.log('🔧 EEBC Theme Fix - Nettoyage localStorage');
    
    // Nettoyer les anciennes clés localStorage incorrectes
    const oldKeys = ['theme', 'eebc_theme', 'dashboard-theme'];
    let cleaned = 0;
    
    oldKeys.forEach(key => {
        if (localStorage.getItem(key)) {
            localStorage.removeItem(key);
            cleaned++;
            console.log(`   ❌ Supprimé: ${key}`);
        }
    });
    
    if (cleaned > 0) {
        console.log(`   ✅ ${cleaned} anciennes clés nettoyées`);
    }
    
    // Vérifier la clé correcte
    const currentTheme = localStorage.getItem('eebc-theme');
    if (currentTheme) {
        console.log(`   ✅ Thème actuel: ${currentTheme}`);
        // Forcer la réapplication
        document.documentElement.setAttribute('data-theme', currentTheme);
    } else {
        // Appliquer le thème par défaut
        const defaultTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'darkly' : 'default';
        localStorage.setItem('eebc-theme', defaultTheme);
        document.documentElement.setAttribute('data-theme', defaultTheme);
        console.log(`   ✅ Thème par défaut appliqué: ${defaultTheme}`);
    }
    
    // Vérifier que l'attribut data-theme est bien appliqué
    const appliedTheme = document.documentElement.getAttribute('data-theme');
    console.log(`   🎨 Thème appliqué au DOM: ${appliedTheme}`);
    
    // Déclencher un événement pour notifier les composants
    window.dispatchEvent(new CustomEvent('themeFixed', { 
        detail: { theme: appliedTheme } 
    }));
    
    console.log('✅ Correction des thèmes terminée');
})();