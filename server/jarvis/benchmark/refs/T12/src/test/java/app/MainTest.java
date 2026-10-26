package app;

import static org.junit.jupiter.api.Assertions.assertEquals;
import org.junit.jupiter.api.Test;

class MainTest {
    @Test void quadrat() { assertEquals(0, Main.quadrat(0)); assertEquals(49, Main.quadrat(7)); assertEquals(9, Main.quadrat(-3)); }
}
