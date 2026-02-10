"""
Script de prueba para verificar el sistema de caché
Ejecutar: python test_cache.py
"""
import asyncio
from utils.cache import permission_cache, users_cache

async def test_cache():
    print("🧪 Probando sistema de caché...\n")
    
    # Test 1: Guardar y recuperar
    print("1️⃣ Test: Guardar y recuperar valor")
    await permission_cache.set("test_key", {"ok": True, "data": "test"})
    result = await permission_cache.get("test_key")
    assert result == {"ok": True, "data": "test"}, "Error: no se recuperó el valor correcto"
    print("   ✅ Valor guardado y recuperado correctamente")
    
    # Test 2: Cache miss
    print("\n2️⃣ Test: Cache miss")
    result = await permission_cache.get("non_existent_key")
    assert result is None, "Error: debería retornar None para clave inexistente"
    print("   ✅ Cache miss funciona correctamente")
    
    # Test 3: Múltiples valores
    print("\n3️⃣ Test: Múltiples valores en caché")
    await users_cache.set("user:1", {"nombre": "Juan", "correo": "juan@test.com"})
    await users_cache.set("user:2", {"nombre": "Maria", "correo": "maria@test.com"})
    
    user1 = await users_cache.get("user:1")
    user2 = await users_cache.get("user:2")
    
    assert user1["nombre"] == "Juan", "Error en user1"
    assert user2["nombre"] == "Maria", "Error en user2"
    print("   ✅ Múltiples valores funcionan correctamente")
    
    # Test 4: Eliminación
    print("\n4️⃣ Test: Eliminación de clave")
    await permission_cache.delete("test_key")
    result = await permission_cache.get("test_key")
    assert result is None, "Error: la clave no fue eliminada"
    print("   ✅ Eliminación funciona correctamente")
    
    # Test 5: Limpieza total
    print("\n5️⃣ Test: Limpieza total del caché")
    await users_cache.clear()
    user1 = await users_cache.get("user:1")
    assert user1 is None, "Error: el caché no fue limpiado"
    print("   ✅ Limpieza total funciona correctamente")
    
    # Test 6: Expiración (simulada con TTL corto)
    print("\n6️⃣ Test: Expiración de caché (TTL)")
    from utils.cache import SimpleCache
    short_cache = SimpleCache(ttl_seconds=1)
    await short_cache.set("expire_test", "value")
    
    # Inmediatamente debe existir
    result = await short_cache.get("expire_test")
    assert result == "value", "Error: valor no guardado"
    print("   ✅ Valor guardado correctamente")
    
    # Después de 2 segundos debe haber expirado
    print("   ⏳ Esperando 2 segundos para que expire...")
    await asyncio.sleep(2)
    result = await short_cache.get("expire_test")
    assert result is None, "Error: el valor no expiró"
    print("   ✅ Expiración por TTL funciona correctamente")
    
    print("\n" + "="*50)
    print("✅ TODOS LOS TESTS PASARON EXITOSAMENTE!")
    print("="*50)
    print("\n📊 El sistema de caché está funcionando correctamente.")
    print("   - Almacenamiento: ✅")
    print("   - Recuperación: ✅")
    print("   - Expiración TTL: ✅")
    print("   - Limpieza: ✅")
    print("\n🚀 Puedes usar el caché en producción con confianza.")

if __name__ == "__main__":
    asyncio.run(test_cache())
